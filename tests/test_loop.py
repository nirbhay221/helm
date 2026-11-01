"""The closed loop must run end to end, keep variance low through a shock, and
buy at least the target each period (Awardsmith meets-or-exceeds)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from arms.awardsmith import DiscountTier, SupplierQuote
from council import HelmLoop
from helm_core import ControllerParams, RecedingHorizonController
from simulator import BusinessParams, BusinessSim


def _loop():
    bp = BusinessParams()
    sim = BusinessSim(bp, seed=7, n_periods=24)
    sim.inject_shock(8, 60.0)
    controller = RecedingHorizonController(
        ControllerParams(unit_cost=bp.unit_cost, price=bp.price, lead_time=bp.lead_time)
    )
    suppliers = [
        SupplierQuote("Gamma", [DiscountTier(10, 7.5)], capacity=60),
        SupplierQuote("Beta", [DiscountTier(10, 8.0)], capacity=120),
        SupplierQuote("Alpha", [DiscountTier(10, 8.3), DiscountTier(90, 7.9)], capacity=120),
    ]
    loop = HelmLoop(sim, controller, suppliers)
    loop.run()
    return loop


def test_loop_runs_full_horizon():
    loop = _loop()
    assert len(loop.journal) == 24
    assert all(e.controller_status in ("Optimal", "Feasible") for e in loop.journal)


def test_loop_closes_variance():
    loop = _loop()
    # end-to-end (controller + real procurement) still holds variance well below
    # the naive policy's ~1600 cumulative deviation seen in the controller demo.
    assert loop.cumulative_deviation() < 600.0


def test_orders_meet_or_exceed_target():
    loop = _loop()
    for e in loop.journal:
        if e.order_target > 1e-6 and e.awardsmith_status in ("Optimal", "Feasible"):
            assert e.ordered_qty >= e.order_target - 1e-6
