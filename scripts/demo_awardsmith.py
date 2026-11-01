"""Awardsmith money shot: the controller's order, bought optimally.

The controller asks for ~100 units. The cheapest supplier (Gamma) cannot fill
the whole order (capacity 60). A human eyeballing it single-sources from the
cheapest supplier that CAN fill it. Awardsmith instead takes Gamma to capacity
and tops up from the next cheapest, beating the best single-supplier choice on
total landed cost. It also honors a diversification cap when asked.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from arms.awardsmith import (  # noqa: E402
    AwardsmithSolver,
    DiscountTier,
    SupplierQuote,
    naive_single_supplier_cost,
)


def suppliers() -> list[SupplierQuote]:
    return [
        SupplierQuote("Gamma", [DiscountTier(10, 7.5)], capacity=60),
        SupplierQuote("Beta", [DiscountTier(10, 8.0)], capacity=120),
        SupplierQuote("Alpha", [DiscountTier(10, 8.3), DiscountTier(90, 7.9)], capacity=120),
    ]


def show(title: str, res) -> None:
    print(title)
    for ln in res.lines:
        print(f"    {ln.supplier:>6}: {ln.quantity:>6.1f} units @ ${ln.unit_price:>4.2f} "
              f"(tier>={ln.tier_min_qty:>3.0f})  = ${ln.line_cost:>8.2f}")
    print(f"    status={res.status}  total={res.total_quantity:.1f} units  cost=${res.total_cost:.2f}")


def main() -> None:
    sup = suppliers()
    Q = 100.0

    solver = AwardsmithSolver(sup)
    res = solver.allocate(Q)
    naive = naive_single_supplier_cost(sup, Q)

    print(f"Controller asked for {Q:.0f} units.\n")
    show("AWARDSMITH optimal allocation:", res)
    saving = naive - res.total_cost
    pct = (saving / naive * 100) if naive not in (0.0, float("inf")) else 0.0
    print(f"\n  naive best-single-supplier cost: ${naive:.2f}")
    print(f"  awardsmith cost:                 ${res.total_cost:.2f}")
    print(f"  saved: ${saving:.2f}  ({pct:.1f}% lower landed cost)\n")

    res2 = solver.allocate(Q, max_share=0.5)
    show("With a diversification cap (no supplier > 50% of the order):", res2)


if __name__ == "__main__":
    main()
