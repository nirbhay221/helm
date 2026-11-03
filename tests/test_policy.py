"""The policy compiler turns English rules into validated, enforced constraints."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.policy import PolicyDesk  # noqa: E402
from marketplace.allocator import AllocCreator, Weights, allocate  # noqa: E402


def _desk():
    from agent.llm import LLMClient
    return PolicyDesk(LLMClient(env={}))      # no key -> fallback compiler


def test_fallback_compiles_diversification_and_risk_rules():
    d = _desk().compile("Pay creators fast, but no more than 20% to any one creator, and hold risky accounts.")
    assert d.constraints.max_fraction_per_creator == 0.2
    assert d.weights.risk == 3.0
    assert d.weights.speed >= 2.0


def test_constraint_caps_a_single_creator_share():
    cs = [AllocCreator("whale", "US", owed=10000, risk=0.1, priority=0.9),
          AllocCreator("b", "US", owed=10000, risk=0.1, priority=0.8)]
    from marketplace.allocator import Constraints
    r = allocate(cs, budget=1000, weights=Weights(1, 1, 1, 1),
                 constraints=Constraints(max_fraction_per_creator=0.3))
    paid = {l["name"]: l["amount"] for l in r.lines}
    assert paid.get("whale", 0) <= 300 + 1e-6      # capped at 30% of the 1000 budget


def test_excluded_country_and_risk_ceiling_hold_creators():
    from marketplace.allocator import Constraints
    cs = [AllocCreator("us", "US", owed=500, risk=0.2, priority=0.9),
          AllocCreator("ng", "NG", owed=500, risk=0.2, priority=0.9),
          AllocCreator("risky", "US", owed=500, risk=0.95, priority=0.9)]
    r = allocate(cs, budget=2000, weights=Weights(1, 1, 0.1, 1),
                 constraints=Constraints(exclude_countries=("NG",), max_risk=0.8))
    names = {l["name"] for l in r.lines}
    assert "ng" not in names and "risky" not in names and "us" in names


def test_weights_are_validated_when_compiled():
    d = _desk().compile("balanced")
    for w in (d.weights.speed, d.weights.tax, d.weights.risk, d.weights.fx):
        assert 0 <= w <= 3
