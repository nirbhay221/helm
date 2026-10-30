"""Quartermaster: buy a target quantity at the lowest total cost across suppliers.

This is the procurement winner-determination problem as a mixed-integer program:
all-units tier discounts, minimum order quantities, capacity, a fixed fee per supplier
used, and a small holding cost on anything bought beyond the target.
"""

from __future__ import annotations

from dataclasses import dataclass

from helm.lp import Model
from helm.model import Order, Supplier


@dataclass(frozen=True)
class BuyPlan:
    orders: tuple[Order, ...]
    total_cost: float
    qty: int
    status: str

    @property
    def ok(self) -> bool:
        return self.status == "optimal"


def solve(
    target: int,
    suppliers: list[Supplier],
    holding_cost: float = 0.5,
    max_overbuy: int | None = None,
    max_share: float = 1.0,
) -> BuyPlan:
    if target <= 0 or not suppliers:
        return BuyPlan((), 0.0, 0, "optimal")
    if max_overbuy is None:
        max_overbuy = max(s.moq for s in suppliers)

    m = Model()
    for s in suppliers:
        tiers = sorted(s.tiers, key=lambda t: t.min_qty)
        for k, tier in enumerate(tiers):
            x = m.var(f"x|{s.id}|{k}", 0, s.capacity, integer=True)
            y = m.binary(f"y|{s.id}|{k}")
            m.add({x: 1, y: -tier.min_qty}, lo=0)  # reaching tier k needs at least its minimum
            m.add({x: 1, y: -s.capacity}, hi=0)  # no quantity unless tier k is chosen
            m.minimize({x: tier.unit_price + holding_cost, y: s.fixed_fee})
        m.add({f"y|{s.id}|{k}": 1 for k in range(len(tiers))}, hi=1)

    total = {name: 1.0 for name in m.names if name.startswith("x|")}
    m.add(total, lo=target, hi=target + max_overbuy)
    if max_share < 1.0:
        cap = max_share * (target + max_overbuy)
        for s in suppliers:
            m.add({n: 1.0 for n in total if n.split("|")[1] == s.id}, hi=max(cap, s.moq))

    sol = m.solve()
    if not sol.ok:
        return BuyPlan((), 0.0, 0, sol.status)

    orders = []
    for s in suppliers:
        qty = round(sum(sol[n] for n in total if n.split("|")[1] == s.id))
        if qty > 0:
            orders.append(Order(s.id, qty, s.unit_price(qty), s.fixed_fee))
    return BuyPlan(tuple(orders), sum(o.cost for o in orders), sum(o.qty for o in orders), sol.status)


def naive(target: int, suppliers: list[Supplier]) -> BuyPlan:
    """What a person usually does: pick the lowest advertised unit price and fill from there."""
    remaining, orders = target, []
    for s in sorted(suppliers, key=lambda s: min(t.unit_price for t in s.tiers)):
        if remaining <= 0:
            break
        qty = min(max(remaining, s.moq), s.capacity)
        orders.append(Order(s.id, qty, s.unit_price(qty), s.fixed_fee))
        remaining -= qty
    status = "optimal" if remaining <= 0 else "short"
    return BuyPlan(tuple(orders), sum(o.cost for o in orders), sum(o.qty for o in orders), status)
