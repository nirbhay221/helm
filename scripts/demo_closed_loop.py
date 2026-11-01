"""Brain + buying arm, end to end, with the control journal printed.

A demand shock hits at period 8. Watch the controller raise its order target,
Awardsmith buy it across suppliers at least cost, and the business snap back to
plan. The journal is what a human (or a judge) reads: per cycle, the decision,
the supplier split, the spend, and the resulting state.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from arms.awardsmith import DiscountTier, SupplierQuote  # noqa: E402
from council import HelmLoop  # noqa: E402
from helm_core import ControllerParams, RecedingHorizonController  # noqa: E402
from simulator import BusinessParams, BusinessSim  # noqa: E402


def main() -> None:
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

    print("HELM control journal (brain decides, Awardsmith buys)")
    print(f"{'t':>2} {'inv_in':>6} {'target':>6} {'bought':>6} {'cost':>8} "
          f"{'inv_out':>7} {'dev':>6}  split")
    for e in loop.journal:
        split = ", ".join(f"{name} {qty:.0f}@{pr:.2f}" for name, qty, pr in e.supplier_split) or "-"
        mark = "  <-- shock" if e.period == 8 else ""
        print(f"{e.period:>2} {e.inventory_before:>6.1f} {e.order_target:>6.1f} "
              f"{e.ordered_qty:>6.1f} {e.order_cost:>8.1f} {e.inventory_after:>7.1f} "
              f"{e.deviation_after:>6.1f}  {split}{mark}")

    print(f"\n  cumulative inventory deviation: {loop.cumulative_deviation():.1f}")
    print(f"  total procurement spend:        {loop.total_spend():.1f}")
    print(f"  final cash:                     {sim.cash:.1f}")


if __name__ == "__main__":
    main()
