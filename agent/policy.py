"""Compile a plain-English treasury policy into an enforceable payout program.

This is the deep use of the model: the operator (or a human) states a policy in
words, and the model compiles it into the optimizer's WEIGHTS plus HARD
CONSTRAINTS, which the solver then obeys. The model does the reading and
interpretation only it can do; it never moves money and never sets a limit the
solver does not re-check. Every compiled field is validated and bounded before
use, because the known failure mode is a policy that compiles cleanly but means
something subtly different (so we also echo back a plain-English reading of what
was compiled, for a human to confirm).

Grounded in the 2026 NL-to-optimization line (EvoOpt-LLM, VeriSimpl, PEARL) and
mirrors how agent-payment governance projects turn a written policy into a
validated, self-enforcing intent.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from marketplace.allocator import TREATY_WITHHOLDING, Constraints, Weights, validate_weights

from .llm import LLMClient

_KNOWN_COUNTRIES = set(TREATY_WITHHOLDING.keys())
_COUNTRY_NAMES = {
    "nigeria": "NG", "china": "CN", "india": "IN", "brazil": "BR", "philippines": "PH",
    "mexico": "MX", "germany": "DE", "canada": "CA", "united states": "US", "usa": "US",
    "u.s.": "US", "america": "US", "united kingdom": "GB", "u.k.": "GB", "uk": "GB", "britain": "GB",
}
_EXCLUDE_WORDS = ("freeze", "stop", "halt", "suspend", "exclude", "no payout", "no payouts",
                  "do not pay", "don't pay", "pending review", "block", "pause")


def _to_code(token: str) -> str | None:
    t = str(token).strip().upper()
    if t in _KNOWN_COUNTRIES:
        return t
    return _COUNTRY_NAMES.get(str(token).strip().lower())

COMPILE_POLICY_TOOL = {
    "type": "function",
    "function": {
        "name": "compile_policy",
        "description": (
            "Compile a plain-English treasury policy into payout objective weights and hard "
            "constraints. Weights (0-3): speed (pay fast/priority), tax (deliver more net), "
            "risk (avoid risky creators), fx (avoid currency cost). Constraints: "
            "max_fraction_per_creator (0-1, cap any one creator's share of the batch), "
            "exclude_countries (2-letter codes to not pay this cycle), max_risk (0-1, never pay "
            "a creator riskier than this), min_priority (0-1, only pay creators at least this "
            "urgent). Translate the policy faithfully; do not invent limits it does not state."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "speed": {"type": "number"}, "tax": {"type": "number"},
                "risk": {"type": "number"}, "fx": {"type": "number"},
                "max_fraction_per_creator": {"type": "number"},
                "exclude_countries": {"type": "array", "items": {"type": "string"}},
                "max_risk": {"type": "number", "description": "Risk ceiling in [0,1]; hold creators riskier than this. 'Hold high-risk' means about 0.7, NOT 0 (0 would pay no one). Leave 1.0 for no ceiling."},
                "min_priority": {"type": "number"},
                "reading": {"type": "string", "description": "Plain-English readback of what you compiled."},
            },
            "required": ["speed", "tax", "risk", "fx"],
        },
    },
}

_SYSTEM = (
    "You compile a creator-payout policy stated in English into weights and hard constraints "
    "by calling compile_policy. Be faithful: only set a constraint the policy actually states. "
    "Weights default near 1. Use max_fraction_per_creator for diversification rules ('no one "
    "more than 20% of a batch' -> 0.2), max_risk to hold risky accounts, exclude_countries for "
    "'do not pay X this week', min_priority to pay only urgent ones. Always give a short reading."
)


@dataclass
class PolicyDecision:
    weights: Weights
    constraints: Constraints
    reading: str = ""
    source: str = "model"
    violations: list = field(default_factory=list)


class PolicyDesk:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient()

    @property
    def available(self) -> bool:
        return bool(self.llm and self.llm.available)

    def compile(self, policy_text: str) -> PolicyDecision:
        if self.available:
            try:
                return self._compile_llm(policy_text)
            except Exception:
                pass
        return self._compile_fallback(policy_text)

    def _compile_llm(self, policy_text: str) -> PolicyDecision:
        msg = self.llm.chat(
            messages=[{"role": "system", "content": _SYSTEM},
                      {"role": "user", "content": f"Policy: {policy_text.strip()}\n\nCompile it."}],
            tools=[COMPILE_POLICY_TOOL],
            tool_choice={"type": "function", "function": {"name": "compile_policy"}},
            temperature=0.0)
        calls = (msg or {}).get("tool_calls") or []
        if not calls:
            return self._compile_fallback(policy_text)
        args = calls[0].get("function", {}).get("arguments", "{}")
        data = args if isinstance(args, dict) else json.loads(args)
        return self._assemble(data, source="model", policy_text=policy_text + " " + str(data.get("reading", "")))

    def _compile_fallback(self, policy_text: str) -> PolicyDecision:
        t = (policy_text or "").lower()
        data = {"speed": 1.0, "tax": 1.0, "risk": 1.0, "fx": 1.0}
        if any(k in t for k in ("fraud", "chargeback", "risky", "hold risky")):
            data["risk"] = 3.0
        if "fast" in t or "quickly" in t or "asap" in t:
            data["speed"] = 2.5
        import re
        m = re.search(r"(\d+(?:\.\d+)?)\s*%", t)
        if m and ("no more than" in t or "cap" in t or "max" in t or "diversif" in t):
            data["max_fraction_per_creator"] = max(0.0, min(1.0, float(m.group(1)) / 100.0))
        data["reading"] = "fallback keyword parse of the policy"
        return self._assemble(data, source="fallback", policy_text=policy_text)

    def _assemble(self, data: dict, source: str, policy_text: str = "") -> PolicyDecision:
        w, wv = validate_weights(data)
        violations = list(wv)

        def _clip01(name, default):
            try:
                v = float(data.get(name, default))
            except (TypeError, ValueError):
                v = default
            if v < 0 or v > 1:
                violations.append(f"{name} {round(v,2)} out of [0,1]; clamped")
                v = max(0.0, min(1.0, v))
            return v

        raw_ex = data.get("exclude_countries") or []
        if isinstance(raw_ex, str):
            raw_ex = [raw_ex]
        codes = {c for c in (_to_code(x) for x in raw_ex) if c}   # accept codes OR names
        # deterministic net: if the policy says freeze/stop and names a country, honor it
        # even when the model left the field empty (a known reliability gap).
        text = (policy_text or "").lower()
        if any(k in text for k in _EXCLUDE_WORDS):
            for nm, code in _COUNTRY_NAMES.items():
                if nm in text:
                    codes.add(code)
        exclude = tuple(sorted(codes))
        dropped = [c for c in raw_ex if not _to_code(c) and str(c).strip().isalpha()]
        if dropped:
            violations.append(f"unknown countries ignored: {dropped}")

        max_risk = _clip01("max_risk", 1.0)
        # Sanity guard against the known semantic error: a near-zero risk ceiling
        # validates but freezes nearly everyone, which "hold high-risk" never means.
        if 0.0 < max_risk < 0.1:
            violations.append(f"max_risk {round(max_risk,2)} would freeze almost all payouts; "
                              "read 'hold high-risk' as 0.7")
            max_risk = 0.7
        con = Constraints(
            max_fraction_per_creator=_clip01("max_fraction_per_creator", 1.0),
            exclude_countries=exclude,
            max_risk=max_risk,
            min_priority=_clip01("min_priority", 0.0))
        return PolicyDecision(weights=w, constraints=con, reading=str(data.get("reading", "")),
                              source=source, violations=violations)
