"""Awardsmith checks: it must never do worse than the best single supplier,
must meet the target, must respect capacity and minimum-order quantities, and
must price all-units tiers correctly (the subtle part)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from arms.awardsmith import (
    AwardsmithSolver,
    DiscountTier,
    SupplierQuote,
    naive_single_supplier_cost,
)


def _scenario():
    return [
        SupplierQuote("Gamma", [DiscountTier(10, 7.5)], capacity=60),
        SupplierQuote("Beta", [DiscountTier(10, 8.0)], capacity=120),
        SupplierQuote("Alpha", [DiscountTier(10, 8.3), DiscountTier(90, 7.9)], capacity=120),
    ]


def test_meets_target_and_optimal():
    s = _scenario()
    res = AwardsmithSolver(s).allocate(100.0)
    assert res.status == "Optimal"
    assert res.total_quantity >= 100.0 - 1e-6


def test_never_worse_than_best_single_supplier():
    s = _scenario()
    res = AwardsmithSolver(s).allocate(100.0)
    naive = naive_single_supplier_cost(s, 100.0)
    assert res.total_cost <= naive + 1e-6


def test_capacity_forces_split_beating_single():
    # cheapest supplier (Gamma, 7.5) can only do 60 of the 100; optimum tops up
    s = _scenario()
    res = AwardsmithSolver(s).allocate(100.0)
    gamma = next((ln for ln in res.lines if ln.supplier == "Gamma"), None)
    assert gamma is not None and gamma.quantity <= 60.0 + 1e-6
    # strictly cheaper than any single supplier that can fill 100 alone
    assert res.total_cost < naive_single_supplier_cost(s, 100.0) - 1e-6


def test_all_units_tier_priced_correctly():
    # one supplier, tiers: 1+ at $10, 50+ at $8 (all-units). Ask for 60 -> all @ $8.
    one = [SupplierQuote("Solo", [DiscountTier(1, 10.0), DiscountTier(50, 8.0)], capacity=200)]
    res = AwardsmithSolver(one).allocate(60.0)
    assert res.status == "Optimal"
    assert len(res.lines) == 1
    assert abs(res.lines[0].unit_price - 8.0) < 1e-9
    assert abs(res.total_cost - 480.0) < 1e-6  # 60 * 8, not 60 * 10


def test_min_order_quantity_respected():
    # MOQ is the first tier's min_qty (20); a tiny target must still respect it
    one = [SupplierQuote("Solo", [DiscountTier(20, 5.0)], capacity=100)]
    res = AwardsmithSolver(one).allocate(5.0)
    assert res.status == "Optimal"
    assert res.total_quantity >= 20.0 - 1e-6  # cannot order below MOQ when used


def test_diversification_cap():
    s = _scenario()
    res = AwardsmithSolver(s).allocate(100.0, max_share=0.5)
    assert res.status == "Optimal"
    assert all(ln.quantity <= 50.0 + 1e-6 for ln in res.lines)
