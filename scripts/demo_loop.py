"""The money shot, in the terminal.

Run the same business, with the same demand and the same shock, under two
policies:
  - naive: reorder the baseline demand every period (what a static budget does),
  - helm:  the receding-horizon controller re-planning from the real state.

A demand shock hits mid-run. The naive policy lets inventory drift off the
target and stay there; Helm detects the drift from the realized state and
re-orders by itself to pull inventory back to plan. The summary prints the
cumulative inventory deviation (the variance) for each; Helm's should be far
lower. No human approval, no PayPal needed for this core demo.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helm_core import ControllerParams, RecedingHorizonController  # noqa: E402
from simulator import BusinessParams, BusinessSim  # noqa: E402


def run(policy: str, shock_period: int, shock_delta: float, seed: int = 7, n: int = 24):
    bp = BusinessParams()
    sim = BusinessSim(bp, seed=seed, n_periods=n)
    sim.inject_shock(shock_period, shock_delta)
    ctrl = RecedingHorizonController(
        ControllerParams(
            horizon=8,
            max_order=200.0,
            unit_cost=bp.unit_cost,
            price=bp.price,
            cash_floor=bp.cash_floor,
            lead_time=bp.lead_time,
        )
    )
    while not sim.done():
        if policy == "naive":
            order = bp.baseline_demand
        else:
            H = ctrl.p.horizon
            dec = ctrl.plan(
                inv0=sim.inventory,
                cash0=sim.cash,
                forecast=sim.forecast(H),
                target=sim.target_trajectory(H + 1),
                pending_arrivals=sim.pipeline_arrivals(H),
            )
            order = dec.order_qty
        sim.step(order)
    return sim


def main() -> None:
    shock_period, shock_delta = 8, 60.0  # a demand spike of +60 units at period 8

    naive = run("naive", shock_period, shock_delta)
    helm = run("helm", shock_period, shock_delta)

    print("HELM controller run (per period)")
    print(f"{'t':>2} {'fcst':>5} {'demand':>7} {'sales':>6} {'inv':>7} "
          f"{'target':>6} {'dev':>6} {'order':>6} {'cash':>9}")
    for o in helm.history:
        marker = "  <-- shock" if o.period == shock_period else ""
        print(f"{o.period:>2} {o.forecast_demand:>5.0f} {o.demand:>7.1f} "
              f"{o.sales:>6.1f} {o.inventory:>7.1f} {o.target_inventory:>6.0f} "
              f"{o.inv_deviation:>6.1f} {o.order_placed:>6.1f} {o.cash:>9.1f}{marker}")

    nd = naive.cumulative_inv_deviation()
    hd = helm.cumulative_inv_deviation()
    reduction = (1 - hd / nd) * 100 if nd else 0.0

    print("\nSUMMARY (same demand, same shock, two policies)")
    print(f"  naive  cumulative inventory deviation: {nd:>9.1f}   min cash: {naive.min_cash():>9.1f}")
    print(f"  helm   cumulative inventory deviation: {hd:>9.1f}   min cash: {helm.min_cash():>9.1f}")
    print(f"  variance closed by Helm: {reduction:>5.1f}% lower than the naive policy")


if __name__ == "__main__":
    main()
