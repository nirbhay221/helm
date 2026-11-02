"""A per-creator ledger with hold-until-window and recoupment.

The hole this closes: before, a creator's earnings were one running number, and a
chargeback just came out of the platform's cash. So we could pay a creator for a
sale that later reversed, and never get it back. Real platforms do two things,
and this models both:

  1. Hold until the window closes. Each sale's earnings are a dated lot and only
     count as SETTLED (safe to pay) once the chargeback window has passed. The
     operator may still choose to release unsettled money early for a creator it
     judges low-risk, but it is doing so knowingly.
  2. Recoup. When a chargeback lands, it first eats the creator's unpaid earnings;
     anything beyond that (money we already paid out) becomes a debt the creator
     owes, which the next earnings pay down before the creator sees a cent. A
     creator's net position can go negative, exactly like Stripe carries a
     connected account negative and recoups from future activity.

Everything is event-based per creator, so a late chargeback or an early release
is handled correctly instead of corrupting a single balance field.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class _Lot:
    period: int
    amount: float       # remaining unpaid earnings from this period's sales


@dataclass
class CreatorState:
    unpaid_lots: list[_Lot] = field(default_factory=list)
    recoup_due: float = 0.0     # money already paid out that a chargeback clawed back
    paid: float = 0.0
    recouped: float = 0.0


class CreatorLedger:
    def __init__(self, chargeback_window: int) -> None:
        self.window = int(chargeback_window)
        self._s: dict[str, CreatorState] = defaultdict(CreatorState)

    def _st(self, creator: str) -> CreatorState:
        return self._s[creator]

    # --- money in -----------------------------------------------------------
    def accrue(self, creator: str, amount: float, period: int) -> None:
        """Record a creator's earnings. New earnings first pay down any debt the
        creator owes from an earlier clawback; only the rest becomes payable."""
        amount = max(0.0, float(amount))
        st = self._st(creator)
        if st.recoup_due > 1e-9 and amount > 0:
            off = min(st.recoup_due, amount)
            st.recoup_due -= off
            st.recouped += off
            amount -= off
        if amount > 1e-9:
            st.unpaid_lots.append(_Lot(period, amount))

    # --- views --------------------------------------------------------------
    def total_unpaid(self, creator: str) -> float:
        return round(sum(l.amount for l in self._st(creator).unpaid_lots), 2)

    def settled_unpaid(self, creator: str, now: int) -> float:
        """Unpaid earnings whose chargeback window has closed (safe to pay)."""
        w = self.window
        return round(sum(l.amount for l in self._st(creator).unpaid_lots
                         if l.period + w <= now), 2)

    def recoup_due(self, creator: str) -> float:
        return round(self._st(creator).recoup_due, 2)

    def net_position(self, creator: str) -> float:
        """What we owe the creator minus what they owe us (can be negative)."""
        return round(self.total_unpaid(creator) - self._st(creator).recoup_due, 2)

    # --- money out ----------------------------------------------------------
    def pay(self, creator: str, amount: float, now: int) -> float:
        """Pay a creator, oldest earnings first. Cannot exceed what is unpaid.
        Returns the amount actually paid."""
        st = self._st(creator)
        amount = min(max(0.0, float(amount)), self.total_unpaid(creator))
        remaining = amount
        while remaining > 1e-9 and st.unpaid_lots:
            lot = st.unpaid_lots[0]
            if lot.amount <= remaining + 1e-9:
                remaining -= lot.amount
                st.unpaid_lots.pop(0)
            else:
                lot.amount -= remaining
                remaining = 0.0
        st.paid += amount - remaining
        return round(amount - remaining, 2)

    # --- reversal -----------------------------------------------------------
    def chargeback(self, creator: str, amount: float, now: int) -> float:
        """A chargeback on a creator's sales. It eats their unpaid earnings first;
        anything beyond that is money already paid out, which becomes a debt the
        creator must repay from future earnings. Returns the clawed-back debt."""
        st = self._st(creator)
        remaining = max(0.0, float(amount))
        while remaining > 1e-9 and st.unpaid_lots:
            lot = st.unpaid_lots[0]
            if lot.amount <= remaining + 1e-9:
                remaining -= lot.amount
                st.unpaid_lots.pop(0)
            else:
                lot.amount -= remaining
                remaining = 0.0
        if remaining > 1e-9:
            st.recoup_due += remaining       # already paid out: claw it back later
        return round(remaining, 2)
