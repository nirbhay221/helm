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
    "You compile a creator-payout policy stated in English into optimizer WEIGHTS and HARD "
    "CONSTRAINTS by calling compile_policy.\n"
    "Weights (0-3) are soft priorities that steer how the fixed budget is split; raise the one "
    "the policy cares about. speed = pay the longest-waiting first; tax = deliver more net; "
    "risk = steer money toward safer creators and away from risky ones; fx = avoid currency "
    "cost. If the policy is about fraud, chargebacks, disputes or holding risky accounts, set "
    "the risk weight high (about 2 to 3) so the allocation actually pulls off risky creators; "
    "add max_risk too only if a ceiling is named.\n"
    "Constraints are hard limits the solver may never break: max_fraction_per_creator caps any "
    "one creator's share ('no one over 20%' -> 0.2); exclude_countries lists 2-letter codes not "
    "paid this cycle ('freeze Nigeria and China' -> ['NG','CN']); max_risk refuses anyone riskier "
    "than it (0-1; 'hold high-risk' is about 0.7, never 0); min_priority pays only creators at "
    "least this urgent.\n"
    "Only set a constraint the policy actually states. Weights default near 1. Always give a "
    "short plain-English reading of what you compiled."
)


@dataclass
class PolicyDecision:
    weights: Weights
    constraints: Constraints
    reading: str = ""
    source: str = "model"
    violations: list = field(default_factory=list)
    compiled: str = ""      # what the solver will actually enforce, written from the numbers


def _readback(w, con) -> str:
    """Plain English generated from the compiled numbers, not from the model's text, so it
    can never claim a limit the solver does not enforce."""
    parts = []
    top = max(("speed", "tax", "risk", "fx"), key=lambda k: getattr(w, k))
    if getattr(w, top) > 1.2:
        parts.append({"speed": "favour the longest-waiting creators", "tax": "favour delivering more net",
                      "risk": "steer money away from risky creators", "fx": "avoid currency costs"}[top])
    if con.max_fraction_per_creator < 1.0:
        parts.append(f"cap any one creator at {con.max_fraction_per_creator:.0%} of the batch")
    if con.exclude_countries:
        parts.append("pay no one in " + ", ".join(con.exclude_countries))
    if con.max_risk < 1.0:
        parts.append(f"hold anyone with risk above {con.max_risk:.2f}")
    if con.min_priority > 0.0:
        parts.append(f"pay only creators with priority at least {con.min_priority:.2f}")
    return ("The solver will " + "; ".join(parts) + ".") if parts else "No hard limits; balanced weights."


_EXCLUDE_WORDS = ("exclude", "freeze", "block", "not pay", "no payouts to", "ban")


def _contradictions(reading: str, policy_text: str, con) -> list:
    """Flag a model reading that claims something the compiled constraints do not do."""
    out = []
    r, p = (reading or "").lower(), (policy_text or "").lower()
    if any(k in r for k in _EXCLUDE_WORDS) and "countr" in r and not con.exclude_countries:
        out.append("the model's reading mentions excluding countries, but none were compiled, so no "
                   "country is excluded")
    if ("all countries" in p or "every country" in p) and any(k in p for k in _EXCLUDE_WORDS):
        out.append("excluding every country would pay no one; the solver needs named countries")
    return out


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
            temperature=0.35)
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
        # The model's judgment drives every field. We only PARSE its output (providers
        # often return each argument as a string) and VERIFY it for soundness: bounds,
        # known countries, degenerate ceilings. We never rewrite what the model decided;
        # a bad decision is surfaced as a violation for the verifier and a human, not
        # silently overridden by hardcoded rules.
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

        # parse exclude_countries whether the model returns a real list, a JSON string,
        # or a comma-separated string, then keep only countries the solver knows.
        raw_ex = data.get("exclude_countries")
        if isinstance(raw_ex, str):
            s = raw_ex.strip()
            try:
                parsed = json.loads(s)
                raw_ex = parsed if isinstance(parsed, list) else [parsed]
            except (ValueError, TypeError):
                raw_ex = [p for p in s.strip("[]").replace("'", "").replace('"', "").split(",")]
        raw_ex = [str(x).strip() for x in (raw_ex or []) if str(x).strip()]
        codes = {c for c in (_to_code(x) for x in raw_ex) if c}   # accept codes OR names
        exclude = tuple(sorted(codes))
        dropped = [c for c in raw_ex if not _to_code(c) and c.isalpha()]
        if dropped:
            violations.append(f"unknown countries ignored: {dropped}")

        max_risk = _clip01("max_risk", 1.0)
        # Soundness readback only: a near-zero ceiling pays almost no one. We flag it so
        # a human sees the consequence, but we leave the model's number in place.
        if 0.0 <= max_risk < 0.1:
            violations.append(f"max_risk {round(max_risk,2)} pays almost no one this cycle")
        con = Constraints(
            max_fraction_per_creator=_clip01("max_fraction_per_creator", 1.0),
            exclude_countries=exclude,
            max_risk=max_risk,
            min_priority=_clip01("min_priority", 0.0))
        reading = str(data.get("reading", ""))
        violations += _contradictions(reading, policy_text, con)
        return PolicyDecision(weights=w, constraints=con, reading=reading,
                              source=source, violations=violations, compiled=_readback(w, con))
