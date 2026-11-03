"""The agent sets the payout objectives' weights from the situation.

This is the multi-objective version of the signal desk: instead of one forecast
bump, the model reads the situation and decides how to trade off paying creators
fast against fraud risk, tax drag and FX cost, by setting a weight on each. The
weights are validated and bounded before the solver sees them (the research's
guardrail against an out-of-range or degenerate objective), so the model steers
the priorities, never the numbers.

With a key the model decides; without one a small rule bumps the risk weight when
the situation mentions fraud or chargebacks, so the pipeline still runs.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from marketplace.allocator import Weights, validate_weights

from .llm import LLMClient

SET_WEIGHTS_TOOL = {
    "type": "function",
    "function": {
        "name": "set_payout_weights",
        "description": (
            "Set how strongly to weigh each competing objective when allocating this "
            "cycle's creator payouts. Each weight is 0 to 3. speed = pay creators fast / "
            "honor priority; tax = prefer delivering more net to creators (less lost to "
            "withholding); risk = avoid paying risky creators; fx = avoid currency "
            "conversion cost. Raise risk when fraud or chargebacks are flagged."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "speed": {"type": "number"}, "tax": {"type": "number"},
                "risk": {"type": "number"}, "fx": {"type": "number"},
                "rationale": {"type": "string"},
            },
            "required": ["speed", "tax", "risk", "fx"],
        },
    },
}

_SYSTEM = (
    "You set the weights for a creator-payout optimizer. Read the situation and call "
    "set_payout_weights with speed, tax, risk, fx each in [0,3]. Default near 1 each. "
    "If the situation flags fraud, a chargeback wave, or risky accounts, raise risk "
    "well above the others. If cash is tight, you may raise tax (deliver more net) and "
    "lower speed. Give a short rationale."
)

_RISKY = ("fraud", "chargeback", "risky", "dispute", "scam", "suspicious")


@dataclass
class WeightDecision:
    weights: Weights
    rationale: str = ""
    source: str = "model"          # "model" | "fallback"
    violations: list = None

    def as_dict(self) -> dict:
        w = self.weights
        return {"speed": w.speed, "tax": w.tax, "risk": w.risk, "fx": w.fx,
                "rationale": self.rationale, "source": self.source}


class WeightDesk:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient()

    @property
    def available(self) -> bool:
        return bool(self.llm and self.llm.available)

    def decide(self, situation: str) -> WeightDecision:
        if self.available:
            try:
                return self._decide_llm(situation)
            except Exception:
                pass
        return self._decide_fallback(situation)

    def _decide_llm(self, situation: str) -> WeightDecision:
        msg = self.llm.chat(
            messages=[{"role": "system", "content": _SYSTEM},
                      {"role": "user", "content": f"Situation: {situation.strip()}\n\nSet the weights."}],
            tools=[SET_WEIGHTS_TOOL],
            tool_choice={"type": "function", "function": {"name": "set_payout_weights"}},
            temperature=0.0)
        calls = (msg or {}).get("tool_calls") or []
        if not calls:
            return self._decide_fallback(situation)
        args = calls[0].get("function", {}).get("arguments", "{}")
        data = args if isinstance(args, dict) else json.loads(args)
        w, violations = validate_weights(data)
        return WeightDecision(weights=w, rationale=str(data.get("rationale", "")),
                              source="model", violations=violations)

    def _decide_fallback(self, situation: str) -> WeightDecision:
        text = (situation or "").lower()
        raw = {"speed": 1.0, "tax": 1.0, "risk": 1.0, "fx": 1.0}
        if any(k in text for k in _RISKY):
            raw["risk"] = 3.0
            rationale = "fallback: fraud/chargeback flagged, risk weight raised"
        else:
            rationale = "fallback: balanced weights"
        w, violations = validate_weights(raw)
        return WeightDecision(weights=w, rationale=rationale, source="fallback",
                              violations=violations)
