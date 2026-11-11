"""A small, provider-agnostic chat client with tool-calling.

Helm's brain is a language model that decides which deterministic tools to call.
Any OpenAI-compatible chat endpoint works: the provider, key and model are read
from the environment (HELM_LLM_BASE_URL / HELM_LLM_API_KEY / HELM_LLM_MODEL), so
the code names no vendor. If no key is set, `available` is False and the agent
falls back to a scripted policy, so the system still runs end to end with no key.

Resilience: hosted models rate-limit (HTTP 429) and occasionally fail (5xx). A
multi-agent cycle makes several calls in a few seconds, so one throttled call must
not silently drop the whole cycle to the fallback. Each call therefore retries
transient failures, honouring the provider's suggested wait, and can then move on
to the models listed in HELM_LLM_FALLBACK_MODELS (comma separated). Providers meter
each model separately, so a short chain multiplies headroom. `last_model` records
which model actually answered, so the UI never claims a model it did not use.
"""
from __future__ import annotations

import json
import os
import re
import time

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct"

_TRANSIENT = {408, 409, 425, 429, 500, 502, 503, 504}
_WAIT_IN_BODY = re.compile(r"try again in\s+(?:(\d+)m)?\s*([\d.]+)\s*(ms|s)", re.I)


def _is_openai_reasoning(name: str) -> bool:
    """OpenAI's reasoning families (gpt-5*, o1/o3/o4*), which use a different request shape."""
    n = (name or "").lower().split("/")[-1]
    return n.startswith("gpt-5") or bool(re.match(r"o[134](-|$)", n))


class LLMClient:
    def __init__(self, env: dict | None = None, sleep=time.sleep) -> None:
        env = env if env is not None else os.environ
        self.base_url = (env.get("HELM_LLM_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.api_key = env.get("HELM_LLM_API_KEY", "") or ""
        self.model = env.get("HELM_LLM_MODEL") or DEFAULT_MODEL
        self.timeout = float(env.get("HELM_LLM_TIMEOUT", "60") or "60")
        self.fallback_models = [m.strip() for m in
                                (env.get("HELM_LLM_FALLBACK_MODELS", "") or "").split(",") if m.strip()]
        self.max_retries = int(env.get("HELM_LLM_MAX_RETRIES", "2") or "2")
        self.max_wait = float(env.get("HELM_LLM_MAX_WAIT", "8") or "8")
        # Optional provider hint for reasoning models (e.g. gpt-oss on Groq): lower effort spends fewer
        # hidden reasoning tokens, which count against the per-minute token budget.
        self.reasoning_effort = (env.get("HELM_LLM_REASONING_EFFORT", "") or "").strip() or None
        self.last_model: str | None = None
        self.used_models: list[str] = []          # every model that answered, in order
        self._sleep = sleep

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def _wait_for(self, resp, attempt: int) -> float:
        """Seconds to wait before retrying: the provider's hint if it gave one,
        else exponential backoff; always capped so a demo click never hangs."""
        hint = None
        ra = resp.headers.get("retry-after") if resp is not None else None
        if ra:
            try:
                hint = float(ra)
            except ValueError:
                hint = None
        if hint is None and resp is not None:
            m = _WAIT_IN_BODY.search(resp.text or "")
            if m:
                mins, val, unit = m.groups()
                hint = float(val) / (1000.0 if unit.lower() == "ms" else 1.0) + 60.0 * float(mins or 0)
        if hint is None:
            hint = 0.5 * (2 ** attempt)
        return max(0.0, min(hint + 0.1, self.max_wait))

    def _post(self, payload: dict):
        import requests
        return requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                # Harmless on providers that ignore them; OpenRouter uses them.
                "HTTP-Referer": "https://github.com/helm",
                "X-Title": "Helm",
            },
            data=json.dumps(payload),
            timeout=self.timeout,
        )

    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str = "auto",
        temperature: float = 0.0,
        max_tokens: int = 700,
        model: str | None = None,
    ) -> dict:
        """One chat-completions turn. Returns the assistant message dict:
        {"role": "assistant", "content": str|None, "tool_calls": [...]|None}.

        `model` overrides the default for this call, so one client can drive a
        panel of different models under the same key/endpoint. An explicit model
        is never swapped for a fallback (the panel depends on model identity)."""
        if not self.available:
            raise RuntimeError("LLMClient has no API key; use the agent's fallback.")
        import requests

        chain = [model] if model else [self.model] + [m for m in self.fallback_models if m != self.model]
        last_err: Exception | None = None
        for pos, name in enumerate(chain):
            has_next = pos < len(chain) - 1
            payload: dict = {"model": name, "messages": messages}
            if _is_openai_reasoning(name):
                # OpenAI reasoning models take max_completion_tokens (hidden reasoning counts toward
                # it, so leave headroom) and only their default temperature
                payload["max_completion_tokens"] = max_tokens + 2000
                if self.reasoning_effort:
                    payload["reasoning_effort"] = self.reasoning_effort
            else:
                payload["temperature"] = temperature
                payload["max_tokens"] = max_tokens
                if self.reasoning_effort and "gpt-oss" in name:  # gpt-oss on Groq accepts it too
                    payload["reasoning_effort"] = self.reasoning_effort
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = tool_choice
            for attempt in range(self.max_retries + 1):
                try:
                    resp = self._post(payload)
                except (requests.Timeout, requests.ConnectionError) as exc:
                    last_err = exc
                    if attempt < self.max_retries:
                        self._sleep(self._wait_for(None, attempt))
                        continue
                    break
                if resp.status_code in _TRANSIENT:
                    last_err = requests.HTTPError(f"{resp.status_code} from {name}: {resp.text[:200]}",
                                                  response=resp)
                    wait = self._wait_for(resp, attempt)
                    if has_next and wait > 2.0:
                        break                               # a long wait: another model answers sooner
                    if attempt < self.max_retries:
                        self._sleep(wait)
                        continue
                    break                                   # exhausted: try the next model
                resp.raise_for_status()                     # 4xx other than throttling is a real error
                data = resp.json()
                if "choices" not in data or not data["choices"]:
                    raise RuntimeError(f"LLM returned no choices: {str(data)[:300]}")
                self.last_model = data.get("model") or name
                self.used_models.append(self.last_model)
                return data["choices"][0]["message"]
        raise last_err or RuntimeError("LLM call failed")
