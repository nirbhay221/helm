"""Multi-objective global payout allocation and weight validation."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marketplace.allocator import (AllocCreator, Weights, allocate,
                                    make_global_creators, validate_weights)


def test_validate_weights_clamps_and_guards():
    w, v = validate_weights({"speed": 9, "tax": -1, "risk": 2, "fx": 1})
    assert 0 <= w.speed <= 3 and w.speed == 3        # 9 clamped to 3
    assert w.tax == 0                                 # -1 clamped to 0
    assert any("speed" in m for m in v) and any("tax" in m for m in v)
    w2, v2 = validate_weights({"speed": 0, "tax": 0, "risk": 0, "fx": 0})
    assert w2.speed == 1.0 and any("zero" in m for m in v2)


def test_allocation_respects_budget_and_owed():
    cs = [AllocCreator("a", "US", owed=100, risk=0.1, priority=0.9),
          AllocCreator("b", "IN", owed=100, risk=0.1, priority=0.9)]
    r = allocate(cs, budget=120, weights=Weights(1, 1, 1, 1))
    assert r.total_paid <= 120 + 1e-6
    assert all(l["amount"] <= 100 + 1e-6 for l in r.lines)


def test_raising_risk_weight_shifts_pay_away_from_risky_creators():
    # the risky creator is also the higher-priority one, so only the risk weight
    # decides whether it gets paid under a tight budget
    cs = [AllocCreator("safe", "US", owed=100, risk=0.05, priority=0.3),
          AllocCreator("risky", "US", owed=100, risk=0.9, priority=0.9)]
    low = allocate(cs, budget=100, weights=Weights(speed=1, tax=1, risk=0.1, fx=1))
    high = allocate(cs, budget=100, weights=Weights(speed=1, tax=1, risk=3.0, fx=1))
    assert high.risk_exposure < low.risk_exposure        # holds the risky creator more


def test_tax_weight_prefers_higher_net_countries():
    # US withholds 0, NG withholds 30%; a high tax weight should favor US
    cs = [AllocCreator("us", "US", owed=100, risk=0.2, priority=0.5),
          AllocCreator("ng", "NG", owed=100, risk=0.2, priority=0.5)]
    r = allocate(cs, budget=100, weights=Weights(speed=0, tax=3, risk=0, fx=0))
    paid = {l["name"]: l["amount"] for l in r.lines}
    assert paid.get("us", 0) >= paid.get("ng", 0)


def test_scales_to_many_creators():
    cs = make_global_creators(300, seed=1)
    r = allocate(cs, budget=50000, weights=Weights(1, 1, 1, 1))
    assert r.status in ("Optimal", "Feasible")
    assert r.total_paid <= 50000 + 1e-6
    assert r.paid_count > 0
