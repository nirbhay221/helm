"""The sound verifier bank: the LLM proposes, these dispose.

Following the LLM-Modulo pattern (Kambhampati et al., ICML 2024): an
auto-regressive model cannot be trusted to plan or self-check, so every action
it proposes is passed through deterministic critics that are SOUND, meaning if a
check passes the property it guarantees really holds. The model cannot talk its
way past any of them. Three properties matter for Helm, which moves real money:

  1. Decision authority: the order quantity is the receding-horizon controller's
     recommendation, not the model's. A model-proposed quantity is only ever
     compared against it; the authoritative number wins.
  2. Hard cash-floor: the soft cash penalty in the LP is not a guarantee, so the
     verifier enforces a hard one: an order whose cost would push cash below the
     floor is clamped down to what is affordable (or to zero).
  3. Money-movement guards: a payout must be an AUP-permitted purpose, have
     positive amounts, and not exceed cash on hand; the per-batch idempotency
     and human-approval threshold are enforced downstream in the Payouts tool.

Each check returns a Verdict carrying the (possibly repaired) action and a list
of the violations it corrected or blocked, so the journal shows exactly where
the model was overruled.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from arms.awardsmith import AwardsmithSolver, SupplierQuote
from helm_core import RecedingHorizonController
from paypal.mcp_payouts_tool import ALLOWED_PAYOUT_PURPOSES
from simulator import BusinessSim

from .signals import ForecastAdjustment


@dataclass
class Verdict:
    ok: bool                              # True if the action runs (possibly repaired)
    executed_value: float = 0.0           # authoritative quantity / total that will run
    violations: list[str] = field(default_factory=list)
    repaired: bool = False

    def note(self, msg: str, repaired: bool = True) -> None:
        self.violations.append(msg)
        if repaired:
            self.repaired = True


class ActionVerifier:
    def __init__(
        self,
        sim: BusinessSim,
        controller: RecedingHorizonController,
        suppliers: list[SupplierQuote],
        order_tolerance: float = 0.5,
    ) -> None:
        self.sim = sim
        self.controller = controller
        self.suppliers = suppliers
        self.awardsmith = AwardsmithSolver(suppliers)
        self.tol = order_tolerance

    # --- the authoritative order quantity -----------------------------------
    def controller_recommendation(self) -> float:
        H = self.controller.p.horizon
        dec = self.controller.plan(
            inv0=self.sim.inventory,
            cash0=self.sim.cash,
            forecast=self.sim.forecast(H),
            target=self.sim.target_trajectory(H + 1),
            pending_arrivals=self.sim.pipeline_arrivals(H),
        )
        return max(0.0, float(dec.order_qty))

    def _order_cost(self, qty: float) -> tuple[float, float]:
        """(awarded_qty, cost) for ordering `qty`, via the sourcing MILP."""
        if qty <= 0:
            return 0.0, 0.0
        res = self.awardsmith.allocate(qty)
        if res.status in ("Optimal", "Feasible") and res.total_quantity > 0:
            return res.total_quantity, res.total_cost
        return 0.0, 0.0

    def verify_order(self, proposed_qty: float) -> Verdict:
        """The controller's recommendation is authoritative. A model-proposed
        quantity is overruled if it differs, and the result is clamped so the
        order never breaches the hard cash floor."""
        rec = self.controller_recommendation()
        v = Verdict(ok=True, executed_value=rec)

        try:
            proposed = float(proposed_qty)
        except (TypeError, ValueError):
            proposed = rec
        if abs(proposed - rec) > self.tol:
            v.note(f"model proposed order {round(proposed, 2)}; controller authority "
                   f"is {round(rec, 2)} and wins")

        qty = rec
        if qty > self.controller.p.max_order:
            v.note(f"order {round(qty, 2)} exceeds per-period cap "
                   f"{self.controller.p.max_order}; clamped")
            qty = self.controller.p.max_order

        # hard cash-floor: do not spend below the floor on this order
        awarded, cost = self._order_cost(qty)
        floor = self.sim.p.cash_floor
        if cost > 0 and self.sim.cash - cost < floor:
            affordable_budget = max(0.0, self.sim.cash - floor)
            cheapest_unit = min(
                (t.unit_price for s in self.suppliers for t in s.tiers),
                default=self.controller.p.unit_cost,
            )
            max_units = affordable_budget / cheapest_unit if cheapest_unit > 0 else 0.0
            v.note(f"order cost {round(cost, 2)} would push cash below floor "
                   f"{floor}; clamped to affordable ~{round(max_units, 1)} units")
            qty = max(0.0, min(qty, max_units))

        v.executed_value = round(qty, 2)
        return v

    # --- forecast adjustment from a signal ----------------------------------
    def verify_forecast_adjustment(
        self,
        adj: ForecastAdjustment,
        current_period: int,
        baseline_demand: float,
        horizon: int = 12,
        max_factor: float = 3.0,
    ) -> tuple["Verdict", ForecastAdjustment]:
        """Admit a signal-driven forecast change only within sound bounds.

        The model may inform the plan, not rewrite it. An adjustment is DISCARDED
        if it cites no signal (the known failure mode: inventing demand in noise).
        Surviving deltas are clipped to the planning window and bounded in
        magnitude to +/- max_factor x baseline, and demand is never pushed below
        zero. Returns the verdict and the sanitized adjustment the controller may
        actually use."""
        v = Verdict(ok=True, executed_value=0.0)
        if adj is None or not str(adj.cited_signal).strip():
            v.ok = False
            v.note("forecast adjustment cites no signal; discarded", repaired=False)
            return v, ForecastAdjustment(rationale="rejected: no cited signal",
                                         source=getattr(adj, "source", "model"))

        cap = max_factor * max(1.0, float(baseline_demand))
        lo, hi = current_period, current_period + horizon
        clean: dict[int, float] = {}
        for p, d in (adj.period_deltas or {}).items():
            if p < lo or p > hi:
                v.note(f"delta at period {p} is outside the planning window "
                       f"[{lo},{hi}]; dropped")
                continue
            dd = float(d)
            if abs(dd) > cap:
                v.note(f"delta {round(dd, 1)} at period {p} exceeds bound "
                       f"+/-{round(cap, 1)}; clamped")
                dd = cap if dd > 0 else -cap
            if dd < -baseline_demand:
                dd = -baseline_demand
            if abs(dd) > 1e-9:
                clean[p] = round(dd, 2)

        v.executed_value = round(sum(abs(x) for x in clean.values()), 2)
        sanitized = ForecastAdjustment(
            period_deltas=clean, rationale=adj.rationale,
            cited_signal=adj.cited_signal, source=adj.source,
        )
        return v, sanitized

    # --- money movement -----------------------------------------------------
    def verify_payout(self, recipients: list[dict], purpose: str) -> Verdict:
        total = 0.0
        for r in recipients or []:
            try:
                total += float(r.get("amount", 0))
            except (TypeError, ValueError, AttributeError):
                pass
        v = Verdict(ok=True, executed_value=round(total, 2))

        if (purpose or "").upper() not in ALLOWED_PAYOUT_PURPOSES:
            v.ok = False
            v.note(f"purpose '{purpose}' is not AUP-permitted; blocked", repaired=False)
        if total <= 0:
            v.ok = False
            v.note("payout total is not positive; blocked", repaired=False)
        if total > self.sim.cash:
            v.ok = False
            v.note(f"payout total {round(total, 2)} exceeds cash on hand "
                   f"{round(self.sim.cash, 2)}; blocked", repaired=False)
        return v
