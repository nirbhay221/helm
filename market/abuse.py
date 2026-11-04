"""The both-sides abuse engine: who is actually at fault, and act on it.

Return abuse is a pattern, not a single case (eBay's abusive-buyer policy and the
US INFORM Consumers Act both work this way). The tell for fault is which side the
problem travels with:

  - a SERIAL RETURNER's bad orders span many different sellers  -> the buyer is at fault
  - a BAD SELLER's bad orders span many different buyers        -> the seller is at fault

So the engine flags any account over the return/chargeback threshold, checks how
widely the badness spreads, attributes fault to the side it follows, and acts
(suspend or hold) with a plain-language reason recorded, protecting the innocent
counterparty. A deterministic, auditable judgment the agent can stand behind.
"""
from __future__ import annotations

from dataclasses import dataclass

from .marketplace import Marketplace


@dataclass
class AbuseVerdict:
    account_id: str
    name: str
    role: str                 # "buyer" | "seller"
    bad_count: int            # returns + chargebacks
    rate: float               # fraction of their orders that went bad
    distinct_counterparties: int
    action: str               # "suspend" | "hold" | "watch"
    reason: str
    fault: bool = True


class AbuseEngine:
    def __init__(self, min_bad: int = 10, spread: int = 5,
                 watch_rate: float = 0.30, suspend_rate: float = 0.50) -> None:
        self.min_bad = min_bad          # threshold on returns/chargebacks
        self.spread = spread            # how many distinct counterparties = a real pattern
        self.watch_rate = watch_rate
        self.suspend_rate = suspend_rate

    def _verdict(self, acc, role: str, st: dict) -> AbuseVerdict | None:
        bad, rate, distinct = st["bad"], st["rate"], st["distinct_counterparties"]
        if bad < self.min_bad:
            return None
        # fault requires the badness to spread across many counterparties, so one
        # feud between a single pair does not condemn either side.
        pattern = distinct >= self.spread and rate >= self.watch_rate
        if not pattern:
            return None
        action = "suspend" if rate >= self.suspend_rate else "hold"
        who = "sellers" if role == "buyer" else "buyers"
        kind = "serial returner" if role == "buyer" else "seller who ships bad goods"
        reason = (f"{acc.name} ({role}) has {bad} returns/chargebacks across {distinct} "
                  f"different {who} (rate {int(rate*100)}%), the pattern of a {kind}. "
                  f"Action: {action}; the counterparties are protected.")
        return AbuseVerdict(acc.id, acc.name, role, bad, rate, distinct, action, reason)

    def scan(self, m: Marketplace) -> list[AbuseVerdict]:
        out: list[AbuseVerdict] = []
        for acc in m.accounts.values():
            if acc.status != "active":
                continue
            vb = self._verdict(acc, "buyer", m.buyer_stats(acc.id))
            vs = self._verdict(acc, "seller", m.seller_stats(acc.id))
            # if flagged on both sides, report the worse one
            cand = [v for v in (vb, vs) if v]
            if cand:
                out.append(max(cand, key=lambda v: (v.action == "suspend", v.bad_count)))
        out.sort(key=lambda v: (v.action == "suspend", v.bad_count), reverse=True)
        return out

    def apply(self, m: Marketplace, verdicts: list[AbuseVerdict]) -> int:
        """Enact the suspend verdicts on the marketplace. Returns how many suspended."""
        n = 0
        for v in verdicts:
            if v.action == "suspend":
                m.suspend(v.account_id, v.reason)
                n += 1
        return n
