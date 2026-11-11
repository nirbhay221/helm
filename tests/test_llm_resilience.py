"""The model client survives rate limits and transient failures instead of silently
dropping a multi-agent cycle to the fallback, and it reports the model that answered.

No network: `_post` is replaced by a scripted fake, and `sleep` is captured so the
tests run instantly while still asserting the waits the client chose."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import requests

from agent.llm import LLMClient


class FakeResp:
    def __init__(self, status, body=None, headers=None, text=""):
        self.status_code = status
        self._body = body or {}
        self.headers = headers or {}
        self.text = text

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}", response=self)


def ok(model="m1", content="hi"):
    return FakeResp(200, {"model": model, "choices": [{"message": {"role": "assistant", "content": content}}]})


def client(script, **env):
    waits = []
    base = {"HELM_LLM_API_KEY": "k", "HELM_LLM_MODEL": "m1"}
    base.update(env)
    c = LLMClient(env=base, sleep=waits.append)
    calls = []

    def fake_post(payload):
        calls.append(payload["model"])
        r = script.pop(0)
        if isinstance(r, Exception):
            raise r
        return r
    c._post = fake_post
    return c, calls, waits


def test_retries_a_429_using_the_providers_retry_after():
    c, calls, waits = client([FakeResp(429, headers={"retry-after": "1.5"}), ok()])
    msg = c.chat([{"role": "user", "content": "x"}])
    assert msg["content"] == "hi"
    assert calls == ["m1", "m1"]
    assert waits == [pytest.approx(1.6)]
    assert c.last_model == "m1"


def test_reads_the_wait_from_a_groq_style_error_body():
    body = "Rate limit reached for model ... Please try again in 2.34s. Need more tokens?"
    c, _, waits = client([FakeResp(429, text=body), ok()])
    c.chat([{"role": "user", "content": "x"}])
    assert waits == [pytest.approx(2.44)]


def test_wait_is_capped_so_a_demo_click_never_hangs():
    c, _, waits = client([FakeResp(429, headers={"retry-after": "120"}), ok()], HELM_LLM_MAX_WAIT="5")
    c.chat([{"role": "user", "content": "x"}])
    assert waits == [5.0]


def test_moves_to_the_fallback_model_when_the_primary_stays_throttled():
    script = [FakeResp(429), FakeResp(429), FakeResp(429), ok(model="m2")]
    c, calls, _ = client(script, HELM_LLM_FALLBACK_MODELS="m2, m3")
    c.chat([{"role": "user", "content": "x"}])
    assert calls == ["m1", "m1", "m1", "m2"]
    assert c.last_model == "m2"                    # honest about who answered


def test_explicit_model_is_never_swapped_for_a_fallback():
    script = [FakeResp(429), FakeResp(429), FakeResp(429)]
    c, calls, _ = client(script, HELM_LLM_FALLBACK_MODELS="m2")
    with pytest.raises(requests.HTTPError):
        c.chat([{"role": "user", "content": "x"}], model="panel-model")
    assert calls == ["panel-model"] * 3


def test_a_real_client_error_is_not_retried():
    c, calls, waits = client([FakeResp(401)], HELM_LLM_FALLBACK_MODELS="m2")
    with pytest.raises(requests.HTTPError):
        c.chat([{"role": "user", "content": "x"}])
    assert calls == ["m1"] and waits == []


def test_connection_errors_are_retried():
    c, calls, _ = client([requests.ConnectionError("reset"), ok()])
    assert c.chat([{"role": "user", "content": "x"}])["content"] == "hi"
    assert calls == ["m1", "m1"]


def test_no_key_still_means_fallback():
    c = LLMClient(env={})
    assert not c.available
    with pytest.raises(RuntimeError):
        c.chat([{"role": "user", "content": "x"}])


def test_a_long_throttle_switches_model_instead_of_waiting():
    script = [FakeResp(429, headers={"retry-after": "30"}), ok(model="m2")]
    c, calls, waits = client(script, HELM_LLM_FALLBACK_MODELS="m2")
    c.chat([{"role": "user", "content": "x"}])
    assert calls == ["m1", "m2"] and waits == []       # no 8s stall when another model is free
    assert c.used_models == ["m2"]


def test_used_models_records_every_answering_model():
    c, _, _ = client([ok(model="m1"), FakeResp(429, headers={"retry-after": "30"}), ok(model="m2")],
                     HELM_LLM_FALLBACK_MODELS="m2")
    c.chat([{"role": "user", "content": "a"}])
    c.chat([{"role": "user", "content": "b"}])
    assert c.used_models == ["m1", "m2"]


def test_openai_reasoning_models_get_their_request_shape():
    from agent.llm import LLMClient
    sent = []

    class R:
        status_code, headers, text = 200, {}, ""

        def raise_for_status(self):
            pass

        def json(self):
            return {"model": "gpt-5-nano", "choices": [{"message": {"role": "assistant", "content": "ok"}}]}

    for model, effort in (("gpt-5-nano", "minimal"), ("openai/gpt-oss-120b", "low")):
        c = LLMClient(env={"HELM_LLM_API_KEY": "k", "HELM_LLM_MODEL": model, "HELM_LLM_REASONING_EFFORT": effort})
        c._post = lambda p: (sent.append(p), R())[1]
        c.chat([{"role": "user", "content": "hi"}], temperature=0.3, max_tokens=100)
    five, oss = sent
    assert "temperature" not in five and "max_tokens" not in five
    assert five["max_completion_tokens"] >= 100 and five["reasoning_effort"] == "minimal"
    assert oss["temperature"] == 0.3 and oss["max_tokens"] == 100 and oss["reasoning_effort"] == "low"
