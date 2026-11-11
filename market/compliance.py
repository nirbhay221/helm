"""Banking-grade screening on money going out, before it moves.

Paying creators and suppliers automatically is attractive, but an autonomous payout
agent must apply the controls a bank's payments team would, deterministically, before
release. This screens each outbound payment and returns allow / hold / block with the
reasons, so a model never gets to wave a payment through:

  - sanctions: the payee is on a denylist (stand-in for OFAC/SDN screening);
  - structuring: many sub-threshold payments to one payee summing over the reporting
    threshold in a short window (smurfing to stay under 1099-K/CTR reporting);
  - velocity: an abnormal burst of payments to one payee in the window;
  - duplicate: the same payee and amount seen again inside the window (double pay).

Grounded in AML controls: OFAC sanctions screening, structuring/CTR reporting rules,
velocity and duplicate-payment checks. Deterministic; the thresholds are explicit.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional


# A tiny stand-in denylist. In production this is the OFAC SDN list and PEP/adverse-media.
_SANCTIONS = {"blocked payee", "sanctioned entity", "ofac test", "sdn sample"}

STRUCTURING_THRESHOLD = 10000.0     # the reporting line structuring tries to stay under (CTR-style)
STRUCTURING_WINDOW = 86400          # seconds (one day)
VELOCITY_MAX = 5                    # payments to one payee in the window before it is abnormal


@dataclass
class ComplianceEngine:
    denylist: set = field(default_factory=lambda: set(_SANCTIONS))
    window_seconds: int = STRUCTURING_WINDOW
    history: list = field(default_factory=list)      # (payee, amount, ts)

    def _recent(self, payee: str, now: float):
        return [h for h in self.history if h[0] == payee and now - h[2] <= self.window_seconds]

    def screen(self, payee: str, amount: float, now: Optional[float] = None) -> dict:
        """Screen one outbound payment. Returns {decision, reasons, checks}."""
        now = time.time() if now is None else now
        name = str(payee or "").strip().lower()
        amount = round(float(amount), 2)
        recent = self._recent(name, now)
        reasons, decision = [], "allow"

        if name in self.denylist:
            reasons.append("sanctions: payee is on the denylist")
            decision = "block"

        recent_sum = round(sum(h[1] for h in recent) + amount, 2)
        if len(recent) >= 1 and amount < STRUCTURING_THRESHOLD and recent_sum >= STRUCTURING_THRESHOLD:
            reasons.append("structuring: sub-threshold payments summing to %.2f over %.0f in the window"
                           % (recent_sum, STRUCTURING_THRESHOLD))
            decision = "block" if decision != "block" else decision

        if len(recent) >= VELOCITY_MAX:
            reasons.append("velocity: %d payments to this payee in the window" % (len(recent) + 1))
            if decision == "allow":
                decision = "hold"

        if any(abs(h[1] - amount) < 0.01 for h in recent):
            reasons.append("duplicate: same payee and amount already paid in the window")
            if decision == "allow":
                decision = "hold"

        if decision != "block":
            self.history.append((name, amount, now))     # only record payments that could proceed
        return {"payee": payee, "amount": amount, "decision": decision,
                "reasons": reasons or ["clean"],
                "checks": ["sanctions", "structuring", "velocity", "duplicate"]}
