"""The closed loop: sense -> decide -> act, written to a control journal.

Each period Helm:
  1. senses the real state (inventory, cash, pending orders),
  2. decides a continuous order target with the controller,
  3. turns that target into a concrete, cheapest purchase with Awardsmith,
  4. acts: the purchase is placed and paid (this is where PayPal Orders settles
     the supplier payment in the live build); the business advances,
  5. records everything in a control journal row.

The journal is the kept artifact and the audit trail: for every cycle, the
variance, the decision, the supplier split, the cost, and the resulting state.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from arms.awardsmith import AwardsmithSolver, SupplierQuote
from helm_core import RecedingHorizonController
from simulator import BusinessSim


@dataclass
class JournalEntry:
    period: int
    inventory_before: float
    order_target: float          # what the controller asked for
    ordered_qty: float           # what Awardsmith actually bought (>= target, MOQ/capacity)
    order_cost: float            # what it cost (real supplier pricing)
    supplier_split: list[tuple[str, float, float]]  # (supplier, qty, unit_price)
    controller_status: str
    awardsmith_status: str
    inventory_after: float
    cash_after: float
    target_inventory: float

    @property
    def deviation_after(self) -> float:
        return round(abs(self.inventory_after - self.target_inventory), 2)


class HelmLoop:
    def __init__(
        self,
        sim: BusinessSim,
        controller: RecedingHorizonController,
        suppliers: list[SupplierQuote],
    ) -> None:
        self.sim = sim
        self.controller = controller
        self.awardsmith = AwardsmithSolver(suppliers)
        self.journal: list[JournalEntry] = []

    def run(self) -> list[JournalEntry]:
        while not self.sim.done():
            H = self.controller.p.horizon
            dec = self.controller.plan(
                inv0=self.sim.inventory,
                cash0=self.sim.cash,
                forecast=self.sim.forecast(H),
                target=self.sim.target_trajectory(H + 1),
                pending_arrivals=self.sim.pipeline_arrivals(H),
            )
            target = dec.order_qty

            ordered, cost, split, a_status = 0.0, None, [], "skipped"
            if target > 1e-6:
                award = self.awardsmith.allocate(target)
                a_status = award.status
                if award.status in ("Optimal", "Feasible") and award.total_quantity > 0:
                    ordered = award.total_quantity
                    cost = award.total_cost
                    split = [(ln.supplier, ln.quantity, ln.unit_price) for ln in award.lines]
                else:
                    # fallback so the loop never stalls: order the target at list price
                    ordered = target

            inv_before = self.sim.inventory
            obs = self.sim.step(ordered, cost)
            recorded_cost = cost if cost is not None else round(self.sim.p.unit_cost * ordered, 2)

            self.journal.append(
                JournalEntry(
                    period=obs.period,
                    inventory_before=round(inv_before, 2),
                    order_target=round(target, 2),
                    ordered_qty=round(ordered, 2),
                    order_cost=round(recorded_cost, 2),
                    supplier_split=split,
                    controller_status=dec.status,
                    awardsmith_status=a_status,
                    inventory_after=obs.inventory,
                    cash_after=obs.cash,
                    target_inventory=obs.target_inventory,
                )
            )
        return self.journal

    def cumulative_deviation(self) -> float:
        return round(sum(e.deviation_after for e in self.journal), 2)

    def total_spend(self) -> float:
        return round(sum(e.order_cost for e in self.journal), 2)
