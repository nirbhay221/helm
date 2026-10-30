"""Navigator: the receding-horizon controller at the centre of Helm.

Each cycle it plans the next H weeks across low, middle and high demand scenarios and
commits only this week's move, which is shared by all scenarios (later weeks may differ
per scenario, so the plan hedges instead of betting on one forecast). Levers:

  * how much to order from each lead-time class of suppliers,
  * the affiliate commission rate, which moves demand.

It tracks the owner's inventory and cash targets, never plans below the cash floor
without paying a heavy penalty, and models PayPal holding part of a sales spike.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from helm.forecast.conformal import Forecast
from helm.lp import Model
from helm.model import BusinessPlan, Limits, State, Supplier
from helm.sim.twin import HoldRule


@dataclass(frozen=True)
class SupplyClass:
    lead_weeks: int
    unit_cost: float
    weekly_capacity: float
    min_order: int


@dataclass(frozen=True)
class Weights:
    inventory: float = 1.0  # per unit away from target
    cash: float = 0.05  # per dollar below the cash target (being ahead of plan is not a deviation to fix)
    profit: float = 0.01  # per dollar of cash at the end of the horizon, so spare cash is not burned
    lost_sale: float = 6.0  # per unit of demand not served
    floor_breach: float = 50.0  # per dollar below the cash floor
    commission_step: float = 0.05  # largest weekly change in commission rate


@dataclass(frozen=True)
class NavPlan:
    status: str
    order_qty: dict[int, float]  # lead weeks -> units to order this week
    commission_rate: float
    inventory_path: np.ndarray  # middle scenario, end of each week
    cash_path: np.ndarray
    objective: float

    @property
    def ok(self) -> bool:
        return self.status == "optimal"


def supply_classes(suppliers: list[Supplier]) -> list[SupplyClass]:
    classes = []
    for lead in sorted({s.lead_weeks for s in suppliers}):
        group = [s for s in suppliers if s.lead_weeks == lead]
        cost = min(min(t.unit_price for t in s.tiers) for s in group)
        classes.append(SupplyClass(lead, cost, sum(s.capacity for s in group), min(s.moq for s in group)))
    return classes


def plan(
    state: State,
    fc: Forecast,
    business: BusinessPlan,
    limits: Limits,
    suppliers: list[Supplier],
    affiliate_share: float,
    elasticity: float,
    hold: HoldRule | None = None,
    weights: Weights | None = None,
) -> NavPlan:
    w = weights or Weights()
    hold = hold or HoldRule()
    classes = supply_classes([s for s in suppliers if s.id in limits.allowed_suppliers])
    H = len(fc.point)
    w0 = state.week
    p = business.price
    m = Model()
    trailing = np.mean(state.demand_history[-4:]) if state.demand_history else fc.point[0]

    def target(series: tuple[float, ...], t: int) -> float:
        return series[min(w0 + t, len(series) - 1)]

    def shared(name: str, t: int, s: int, lb: float, ub: float) -> str:
        key = f"{name}_{t}" if t == 0 else f"{name}_{t}_{s}"
        if key not in m.index:
            m.var(key, lb, ub)
        return key

    mid_inv, mid_cash = [], []
    for s, (prob, demand) in enumerate(fc.scenarios()):
        inv_prev: dict[str, float] = {}
        inv_const = state.on_hand
        cash_prev: dict[str, float] = {}
        cash_const = state.cash
        hold_carry: dict[int, dict[str, float]] = {}
        c_prev: str | None = None
        for t in range(H):
            wk = w0 + t
            c = shared("comm", t, s, limits.commission_min, limits.commission_max)
            if c_prev is None:
                m.add({c: 1}, lo=state.commission_rate - w.commission_step, hi=state.commission_rate + w.commission_step)
            else:
                m.add({c: 1, c_prev: -1}, lo=-w.commission_step, hi=w.commission_step)
            c_prev = c

            # Arrivals: known pipeline plus orders this plan places that land this week.
            arrivals: dict[str, float] = {}
            arr_const = state.arrivals(wk)
            spend: dict[str, float] = {}
            for k, cl in enumerate(classes):
                q = shared(f"q{k}", t, s, 0, cl.weekly_capacity)
                spend[q] = cl.unit_cost
                if t - cl.lead_weeks >= 0:
                    arrivals[shared(f"q{k}", t - cl.lead_weeks, s, 0, cl.weekly_capacity)] = 1.0

            sales = m.var(f"sales_{t}_{s}")
            lost = m.var(f"lost_{t}_{s}")
            lift = elasticity * affiliate_share
            d = float(demand[t])
            # lost = demand(c) - sales, with demand(c) = d * (1 + lift * (c - c_now))
            m.eq({lost: 1, sales: 1, c: -d * lift}, d * (1 - lift * state.commission_rate))

            inv = m.var(f"inv_{t}_{s}")
            terms = {inv: 1.0, sales: 1.0, **{k: -v for k, v in inv_prev.items()}}
            for k, v in arrivals.items():
                terms[k] = terms.get(k, 0.0) - v
            m.eq(terms, inv_const + arr_const)

            # Expected PayPal hold when this week looks like a spike.
            hold_frac = hold.hold_fraction if d > hold.spike_ratio * trailing else 0.0
            cash = m.var(f"cash_{t}_{s}", lb=-np.inf)
            cterms = {cash: 1.0, sales: -p * (1 - hold_frac), c: p * affiliate_share * d}
            for k, v in cash_prev.items():
                cterms[k] = cterms.get(k, 0.0) - v
            for k, v in spend.items():
                cterms[k] = cterms.get(k, 0.0) + v
            for k, v in hold_carry.pop(t, {}).items():
                cterms[k] = cterms.get(k, 0.0) - v
            if hold_frac > 0:
                hold_carry.setdefault(t + hold.hold_weeks, {})[sales] = p * hold_frac
            m.eq(cterms, cash_const + state.releases(wk))

            if t == 0:
                m.add({k: v for k, v in spend.items()}, hi=min(limits.max_spend_per_week, state.cash + state.releases(wk)))

            breach = m.var(f"breach_{t}_{s}")
            m.add({cash: 1, breach: 1}, lo=business.cash_floor)

            di_p, di_n = m.var(f"dip_{t}_{s}"), m.var(f"din_{t}_{s}")
            m.eq({inv: 1, di_p: -1, di_n: 1}, target(business.inventory_target, t + 1))
            dc_p, dc_n = m.var(f"dcp_{t}_{s}"), m.var(f"dcn_{t}_{s}")
            m.eq({cash: 1, dc_p: -1, dc_n: 1}, target(business.cash_target, t + 1))

            m.minimize({
                di_p: prob * w.inventory, di_n: prob * w.inventory,
                dc_n: prob * w.cash,
                lost: prob * w.lost_sale, breach: prob * w.floor_breach,
            })
            if t == H - 1:
                m.minimize({cash: -prob * w.profit})
            inv_prev, inv_const = {inv: 1.0}, 0.0
            cash_prev, cash_const = {cash: 1.0}, 0.0
            if s == 1:
                mid_inv.append(inv)
                mid_cash.append(cash)

    sol = m.solve()
    if not sol.ok:
        return NavPlan(sol.status, {}, state.commission_rate, np.array([]), np.array([]), np.inf)
    orders = {cl.lead_weeks: sol[f"q{k}_0"] for k, cl in enumerate(classes)}
    return NavPlan(
        sol.status,
        orders,
        sol["comm_0"],
        np.array([sol[v] for v in mid_inv]),
        np.array([sol[v] for v in mid_cash]),
        sol.objective,
    )
