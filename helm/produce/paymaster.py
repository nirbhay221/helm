"""Paymaster: turn commission owed into a Payouts batch, split exactly to the cent.

This first version splits by each affiliate's share of attributed sales. The sybil-resistant
split (caps, hold-backs until delivery, direct-referral weighting) builds on this.
"""

from __future__ import annotations

from helm.calendar import split_exact
from helm.model import Payout


def batch(owed_cents: int, shares: dict[str, float], min_payout_cents: int = 100) -> list[Payout]:
    if owed_cents < min_payout_cents or not shares:
        return []
    names = list(shares)
    parts = split_exact(owed_cents, [shares[n] for n in names])
    return [Payout(n, c / 100, "commission") for n, c in zip(names, parts) if c > 0]
