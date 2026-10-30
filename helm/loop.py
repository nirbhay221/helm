"""The control loop: sense, forecast, produce, validate, act, confirm, and write it all down.

The orchestrator is a plain state machine, not a language model, so the order of steps and
the retry policy are fixed and auditable. When the Validator rejects a plan, the producer
re-plans with an adjustment that answers the reason (evaluator-optimizer), at most twice.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Protocol

import numpy as np

from helm.forecast.conformal import DemandAdjustment, Forecast, baseline, forecast
from helm.model import Action, BusinessPlan, Limits, Order, State, Supplier
from helm.produce import navigator, quartermaster
from helm.sim.twin import Twin, WeekResult
from helm.validate import gates
from helm.validate.gates import ESCALATE, PASS, Fact, Verdict

MAX_RETRIES = 2


class Executor(Protocol):
    def execute(self, state: State, action: Action) -> WeekResult: ...


@dataclass
class SimExecutor:
    """Executes against the twin. The PayPal executor has the same shape and adds transaction IDs."""

    twin: Twin

    def execute(self, state: State, action: Action) -> WeekResult:
        return self.twin.step(state, action)


@dataclass
class Attempt:
    action: Action
    nav: navigator.NavPlan
    verdicts: list[Verdict]
    adjustment: str


@dataclass
class Cycle:
    week: int
    forecast: Forecast
    attempts: list[Attempt]
    outcome: str  # executed, escalated, held
    executed: Action
    result: WeekResult | None = None
    ghost_inventory: np.ndarray | None = None
    receipts: list[dict] = field(default_factory=list)

    def journal_row(self) -> dict:
        last = self.attempts[-1]
        return {
            "week": self.week,
            "outcome": self.outcome,
            "attempts": len(self.attempts),
            "orders": [(o.supplier_id, o.qty, round(o.cost, 2)) for o in self.executed.orders],
            "commission_rate": self.executed.commission_rate,
            "verdicts": [(v.gate, v.outcome, v.reason) for a in self.attempts for v in a.verdicts],
            "adjustments": [a.adjustment for a in self.attempts if a.adjustment],
            "forecast_next": round(float(self.forecast.point[0]), 1),
            "sales": None if self.result is None else round(self.result.sales, 1),
            "lost": None if self.result is None else round(self.result.lost, 1),
            "held_now": None if self.result is None else round(self.result.held_now, 2),
            "receipts": self.receipts,
            "why": last.nav.status,
        }


@dataclass
class Helm:
    twin: Twin  # the Validator's copy of the world, used only to imagine
    business: BusinessPlan
    limits: Limits
    suppliers: list[Supplier]
    horizon: int = 8
    imagine_runs: int = 200
    journal: list[dict] = field(default_factory=list)

    def produce(self, state: State, fc: Forecast, limits: Limits, weights: navigator.Weights,
                conservative: bool = False) -> tuple[Action, navigator.NavPlan]:
        nav = self._plan(state, fc, limits, weights)
        if conservative:
            # Answer to an instability reject: take the smallest order across nudged forecasts.
            alts = [self._plan(state, _scaled(fc, k), limits, weights) for k in (0.95, 1.05)]
            for lead in nav.order_qty:
                nav.order_qty[lead] = min([nav.order_qty[lead]] + [a.order_qty.get(lead, 0.0) for a in alts])
        orders: list[Order] = []
        allowed = [s for s in self.suppliers if s.id in limits.allowed_suppliers]
        for lead, qty in nav.order_qty.items():
            units = int(round(qty))
            if units <= 0:
                continue
            group = [s for s in allowed if s.lead_weeks == lead]
            if units < 0.5 * min(s.moq for s in group):
                continue  # rounding a tiny need up to a big minimum order wastes cash
            buy = quartermaster.solve(units, group)
            if buy.ok:
                orders.extend(buy.orders)
        return Action(orders=orders, commission_rate=round(nav.commission_rate, 4)), nav

    def cycle(self, state: State, executor: Executor, facts: list[Fact] | None = None) -> Cycle:
        facts = facts or []
        ev = gates.evidence(facts)
        accepted = facts if ev.passed else []
        adjustments = [
            DemandAdjustment(f.value["start_week"], f.value["weeks"], f.value["multiplier"])
            for f in accepted if f.kind == "demand_shift"
        ]
        fc = forecast(state.demand_history, state.week, self.horizon, adjustments=adjustments)
        vfc = baseline(state.demand_history, state.week, self.horizon, adjustments=adjustments)

        limits, weights, conservative, note = self.limits, navigator.Weights(), False, ""
        attempts: list[Attempt] = []
        ghost = None
        outcome, chosen = "held", Action(commission_rate=state.commission_rate)
        for attempt in range(MAX_RETRIES + 1):
            action, nav = self.produce(state, fc, limits, weights, conservative)
            verdicts = [ev] if attempt == 0 else []
            verdicts += self._validate(state, fc, vfc, action, limits, weights)
            if verdicts[-1].gate == "imagine":
                ghost = verdicts[-1].detail.pop("_ghost", None)
            attempts.append(Attempt(action, nav, verdicts, note))
            failed = next((v for v in verdicts if not v.passed and v.gate != "evidence"), None)
            if failed is None:
                outcome, chosen = "executed", action
                break
            if failed.outcome == ESCALATE:
                outcome = "escalated"  # the owner decides; Helm holds its orders meanwhile
                break
            code = failed.detail.get("code", "")
            if code == "cash":
                limits = replace(limits, max_spend_per_week=max(0.0, 0.6 * min(limits.max_spend_per_week, action.spend)))
                note = "cut spend after cash reject"
            elif code == "unstable":
                conservative, note = True, "use the smallest order across nudged forecasts"
            else:
                weights = replace(weights, cash=weights.cash * 4)
                note = "weigh cash more after the plan lost to doing nothing"

        result = executor.execute(state, chosen)
        cycle = Cycle(state.week, fc, attempts, outcome, chosen, result, ghost)
        cycle.receipts = getattr(result, "receipts", [])
        self.journal.append(cycle.journal_row())
        return cycle

    def _plan(self, state: State, fc: Forecast, limits: Limits, weights: navigator.Weights) -> navigator.NavPlan:
        return navigator.plan(
            state, fc, self.business, limits, self.suppliers,
            self.twin.demand.affiliate_share, self.twin.demand.elasticity, self.twin.hold, weights,
        )

    def _validate(self, state: State, fc: Forecast, vfc: Forecast, action: Action, limits: Limits,
                  weights: navigator.Weights) -> list[Verdict]:
        out = [gates.constraints(action, state, self.business, self.suppliers)]
        if not out[-1].passed:
            return out
        out.append(gates.envelope(action, self.limits))  # always the owner's original limits
        if not out[-1].passed:
            return out

        def replan(scale: float) -> tuple[float, float]:
            p = self._plan(state, _scaled(fc, scale), limits, weights)
            return sum(p.order_qty.values()), p.commission_rate

        out.append(gates.stability(replan))
        if not out[-1].passed:
            return out
        verdict, ghost = gates.imagine(self.twin, state, action, vfc, self.business, runs=self.imagine_runs)
        verdict.detail["_ghost"] = ghost.inventory.mean(axis=0)
        out.append(verdict)
        return out


def _scaled(fc: Forecast, k: float) -> Forecast:
    return Forecast(fc.start_week, fc.point * k, fc.lo * k, fc.hi * k, fc.coverage)


def run(helm: Helm, state: State, executor: Executor, weeks: int,
        facts_by_week: dict[int, list[Fact]] | None = None) -> tuple[State, list[Cycle]]:
    cycles = []
    for _ in range(weeks):
        c = helm.cycle(state, executor, (facts_by_week or {}).get(state.week))
        state = c.result.state
        cycles.append(c)
    return state, cycles
