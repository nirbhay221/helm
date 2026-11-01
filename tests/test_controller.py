"""Does the controller actually close variance better than a static policy?

These are the load-bearing checks: the controller must solve reliably, keep
inventory non-negative, and, after a demand shock, track the target far more
tightly than a naive fixed-reorder policy. If the controller did not beat
naive here, the whole premise (a closed loop that corrects drift) would be
theater, so this test is the honest gate.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helm_core import ControllerParams, RecedingHorizonController
from simulator import BusinessParams, BusinessSim


def _run(policy: str, seed: int = 7, n: int = 24, shock=(8, 60.0)):
    bp = BusinessParams()
    sim = BusinessSim(bp, seed=seed, n_periods=n)
    sim.inject_shock(*shock)
    ctrl = RecedingHorizonController(
        ControllerParams(unit_cost=bp.unit_cost, price=bp.price, lead_time=bp.lead_time)
    )
    while not sim.done():
        if policy == "naive":
            order = bp.baseline_demand
        else:
            H = ctrl.p.horizon
            dec = ctrl.plan(
                sim.inventory, sim.cash,
                sim.forecast(H), sim.target_trajectory(H + 1),
                sim.pipeline_arrivals(H),
            )
            assert dec.status == "Optimal"
            assert 0.0 <= dec.order_qty <= ctrl.p.max_order
            order = dec.order_qty
        sim.step(order)
    return sim


def test_controller_solves_and_is_bounded():
    bp = BusinessParams()
    ctrl = RecedingHorizonController(ControllerParams(unit_cost=bp.unit_cost, price=bp.price))
    dec = ctrl.plan(80.0, 2000.0, [40.0] * 8, [120.0] * 9, {})
    assert dec.status == "Optimal"
    assert dec.order_qty >= 0.0


def test_helm_beats_naive_after_shock():
    naive = _run("naive")
    helm = _run("helm")
    nd = naive.cumulative_inv_deviation()
    hd = helm.cumulative_inv_deviation()
    # Helm should cut cumulative inventory variance by a clear margin.
    assert hd < nd * 0.6, f"helm dev {hd} not clearly better than naive dev {nd}"


def test_inventory_never_strongly_negative():
    helm = _run("helm")
    # soft non-negativity; allow a tiny numerical slack
    assert min(o.inventory for o in helm.history) > -1.0
