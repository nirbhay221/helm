"""Awardsmith: the buying arm.

The controller says "acquire about Q units." Awardsmith turns that target into
the cheapest concrete purchase across a set of supplier quotes, respecting:

  - minimum order quantity per supplier (fixed-charge / big-M pattern),
  - supplier capacity,
  - all-units quantity discounts (discontinuous, so modeled with one binary per
    discount tier and the multiple-choice interval formulation, NOT SOS2).

This is the classic supplier-selection-and-order-allocation MILP, which is
NP-hard in general; at the scale of a purchase decision it solves in
milliseconds with branch and bound. Grounded in the standard formulations
(e.g. Stadtler 2007, "A general quantity discount and supplier selection MIP").

All-units discount means: if the chosen quantity from a supplier falls in tier
k, then EVERY unit from that supplier is priced at tier k's unit price. That is
why each tier needs its own binary and quantity variable, with the quantity
boxed into the tier's [lower, upper) range when (and only when) that tier is
selected, and at most one tier selected per supplier used.

Solver: OR-Tools CBC (mixed-integer linear programming).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ortools.linear_solver import pywraplp


@dataclass
class DiscountTier:
    """All-units tier: if order qty >= min_qty (and below the next tier's
    min_qty), every unit is priced at unit_price."""
    min_qty: float
    unit_price: float


@dataclass
class SupplierQuote:
    name: str
    tiers: list[DiscountTier]          # sorted ascending by min_qty; tiers[0].min_qty is the MOQ
    capacity: float                    # max units this supplier can provide
    fixed_cost: float = 0.0            # one-off cost if this supplier is used at all

    def sorted_tiers(self) -> list[DiscountTier]:
        return sorted(self.tiers, key=lambda t: t.min_qty)

    @property
    def moq(self) -> float:
        return self.sorted_tiers()[0].min_qty if self.tiers else 0.0

    def base_price(self) -> float:
        """Cheapest sticker price ignoring volume (used for the naive baseline)."""
        return min((t.unit_price for t in self.tiers), default=float("inf"))


@dataclass
class AwardLine:
    supplier: str
    quantity: float
    unit_price: float
    tier_min_qty: float
    line_cost: float


@dataclass
class AwardResult:
    status: str
    total_cost: float
    total_quantity: float
    lines: list[AwardLine] = field(default_factory=list)


class AwardsmithSolver:
    def __init__(self, suppliers: list[SupplierQuote]) -> None:
        self.suppliers = suppliers

    def allocate(self, target_qty: float, max_share: float | None = None) -> AwardResult:
        """Cheapest purchase that acquires at least `target_qty` units.

        max_share (optional, 0..1): no single supplier may provide more than
        this fraction of target_qty (a diversification / multi-sourcing cap).
        """
        Q = float(target_qty)
        solver = pywraplp.Solver.CreateSolver("CBC")
        if solver is None:  # pragma: no cover
            raise RuntimeError("OR-Tools CBC solver unavailable")

        q_s: dict[str, pywraplp.Variable] = {}
        y_s: dict[str, pywraplp.Variable] = {}
        tier_q: dict[tuple[str, int], pywraplp.Variable] = {}
        tier_x: dict[tuple[str, int], pywraplp.Variable] = {}
        cost_terms = []

        for s in self.suppliers:
            tiers = s.sorted_tiers()
            y = solver.BoolVar(f"use_{s.name}")
            q = solver.NumVar(0.0, s.capacity, f"q_{s.name}")
            y_s[s.name] = y
            q_s[s.name] = q

            tier_qs = []
            tier_xs = []
            for k, tier in enumerate(tiers):
                lower = tier.min_qty
                upper = tiers[k + 1].min_qty if k + 1 < len(tiers) else s.capacity
                x = solver.BoolVar(f"x_{s.name}_{k}")
                qk = solver.NumVar(0.0, upper, f"qk_{s.name}_{k}")
                tier_x[(s.name, k)] = x
                tier_q[(s.name, k)] = qk
                tier_xs.append(x)
                tier_qs.append(qk)
                # box qk into [lower, upper] when and only when tier k is chosen
                solver.Add(qk >= lower * x)
                solver.Add(qk <= upper * x)
                cost_terms.append(tier.unit_price * qk)

            # exactly one tier active iff the supplier is used
            solver.Add(solver.Sum(tier_xs) == y)
            # total from supplier = sum over tiers (only the active tier is nonzero)
            solver.Add(q == solver.Sum(tier_qs))
            # capacity and MOQ gating on "used"
            solver.Add(q <= s.capacity * y)
            solver.Add(q >= s.moq * y)
            if s.fixed_cost:
                cost_terms.append(s.fixed_cost * y)
            if max_share is not None:
                solver.Add(q <= max_share * Q)

        # meet (or exceed) the target quantity
        solver.Add(solver.Sum(list(q_s.values())) >= Q)
        solver.Minimize(solver.Sum(cost_terms))

        result = solver.Solve()
        status = {
            pywraplp.Solver.OPTIMAL: "Optimal",
            pywraplp.Solver.FEASIBLE: "Feasible",
            pywraplp.Solver.INFEASIBLE: "Infeasible",
            pywraplp.Solver.UNBOUNDED: "Unbounded",
            pywraplp.Solver.ABNORMAL: "Abnormal",
            pywraplp.Solver.NOT_SOLVED: "NotSolved",
        }.get(result, "Unknown")

        if status not in ("Optimal", "Feasible"):
            return AwardResult(status=status, total_cost=0.0, total_quantity=0.0, lines=[])

        lines: list[AwardLine] = []
        for s in self.suppliers:
            tiers = s.sorted_tiers()
            for k, tier in enumerate(tiers):
                qk = tier_q[(s.name, k)].solution_value()
                if qk > 1e-6:
                    lines.append(
                        AwardLine(
                            supplier=s.name,
                            quantity=round(qk, 3),
                            unit_price=tier.unit_price,
                            tier_min_qty=tier.min_qty,
                            line_cost=round(tier.unit_price * qk, 2),
                        )
                    )
        total_cost = round(solver.Objective().Value(), 2)
        total_qty = round(sum(line.quantity for line in lines), 3)
        return AwardResult(status=status, total_cost=total_cost, total_quantity=total_qty, lines=lines)


def naive_single_supplier_cost(suppliers: list[SupplierQuote], target_qty: float) -> float:
    """Baseline a human would do: put the whole order with the supplier whose
    sticker (base) price is lowest, at that supplier's applicable all-units tier
    for the full quantity. Returns infinity if nobody has the capacity."""
    Q = float(target_qty)
    best = float("inf")
    for s in suppliers:
        if s.capacity < Q:
            continue
        tiers = s.sorted_tiers()
        unit = tiers[0].unit_price
        for tier in tiers:
            if Q >= tier.min_qty:
                unit = tier.unit_price
        best = min(best, unit * Q + s.fixed_cost)
    return round(best, 2)
