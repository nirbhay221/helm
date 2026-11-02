"""A small, provider-agnostic chat client with tool-calling.

Helm's brain is a language model that decides which deterministic tools to call.
Any OpenAI-compatible chat endpoint works: the provider, key and model are read
from the environment (HELM_LLM_BASE_URL / HELM_LLM_API_KEY / HELM_LLM_MODEL), so
the code names no vendor. If no key is set, `available` is False and the agent
falls back to a scripted policy, so the system still runs end to end with no key.

Only the chat-completions call with `tools` is used; the response is returned as
the raw assistant message (content plus any tool_calls), exactly as the agent
loop needs it.
"""
from __future__ import annotations

import json
import os

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct"


class LLMClient:
    def __init__(self, env: dict | None = None) -> None:
        env = env if env is not None else os.environ
        self.base_url = (env.get("HELM_LLM_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.api_key = env.get("HELM_LLM_API_KEY", "") or ""
        self.model = env.get("HELM_LLM_MODEL") or DEFAULT_MODEL
        self.timeout = float(env.get("HELM_LLM_TIMEOUT", "60") or "60")

    @property
    def available(self) -> bool:
        return bool(self.api_key)

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
        panel of different models under the same key/endpoint."""
        if not self.available:
            raise RuntimeError("LLMClient has no API key; use the agent's fallback.")
        import requests

        payload: dict = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        resp = requests.post(
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
        resp.raise_for_status()
        data = resp.json()
        if "choices" not in data or not data["choices"]:
            raise RuntimeError(f"LLM returned no choices: {str(data)[:300]}")
        return data["choices"][0]["message"]
