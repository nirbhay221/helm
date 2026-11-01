"""Mete: contribution split by true marginal contribution (Shapley value).

When several parties jointly create a pot and their contributions overlap (two
affiliates both touched the same conversion, say), splitting by last-touch or by
raw activity double-counts or mis-credits. The Shapley value is the standard
fair-division answer: each party's average marginal contribution across all
orders in which the coalition could have formed. It is the unique split that is
efficient (shares sum to the whole), symmetric (equal contributors get equal
pay), and gives zero to a party that adds nothing.

Here the "value" of a coalition S is how many conversions S could have produced:
a conversion counts for S if any party that touched it is in S. Shapley value is
computed exactly by enumerating permutations, which is fine for the handful of
parties a payout batch involves.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import permutations


@dataclass
class Contribution:
    party: str
    # the conversions this party touched, by conversion id
    conversions: set = field(default_factory=set)


@dataclass
class MeteResult:
    shares: dict                       # party -> payout amount (sums to pot)
    shapley: dict                      # party -> raw shapley value (sums to #conversions)
    pot: float


def _coalition_value(coalition: frozenset, touched_by: dict) -> int:
    """How many conversions this coalition could have produced: a conversion
    counts if at least one party that touched it is in the coalition."""
    covered = 0
    for parties in touched_by.values():
        if parties & coalition:
            covered += 1
    return covered


def shapley_split(pot: float, contributions: list[Contribution]) -> MeteResult:
    parties = [c.party for c in contributions]
    n = len(parties)
    if n == 0:
        return MeteResult(shares={}, shapley={}, pot=float(pot))

    # conversion id -> set of parties that touched it
    touched_by: dict = {}
    for c in contributions:
        for conv in c.conversions:
            touched_by.setdefault(conv, set()).add(c.party)

    shapley = {p: 0.0 for p in parties}
    perms = list(permutations(parties))
    for order in perms:
        coalition: set = set()
        prev_value = 0
        for p in order:
            coalition.add(p)
            val = _coalition_value(frozenset(coalition), touched_by)
            shapley[p] += val - prev_value
            prev_value = val
    for p in parties:
        shapley[p] /= len(perms)

    total = sum(shapley.values())
    if total <= 0:
        # no conversions: split nothing
        shares = {p: 0.0 for p in parties}
    else:
        shares = {p: round(pot * shapley[p] / total, 2) for p in parties}
    return MeteResult(
        shares=shares,
        shapley={p: round(v, 4) for p, v in shapley.items()},
        pot=float(pot),
    )
