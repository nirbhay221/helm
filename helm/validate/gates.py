"""The Validator: independent checks that try to break a proposed plan before money moves.

It shares no decision code with the producer. It can only pass a plan, reject it with a
reason the producer can act on, or escalate it to the owner. Gates, in order:

  evidence     facts a language model read must quote their source and pass bounds
  constraints  cash floor, budgets, minimums, tier prices and PayPal rules, recomputed
  envelope     inside the owner's limits, or ask the owner
  stability    the plan must not swing wildly when the forecast is nudged
  imagine      run the plan forward in the twin; it must beat doing nothing at low risk
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from helm.forecast.conformal import Forecast
from helm.model import Action, BusinessPlan, Limits, State, Supplier
from helm.sim.twin import Twin

PAYOUT_PURPOSES = {"commission", "rebate", "reward", "incentive"}

PASS, REJECT, ESCALATE = "pass", "reject", "escalate"


@dataclass(frozen=True)
class Fact:
    """Something the Lookout read from text. It only counts once the Evidence gate accepts it."""

    kind: str  # "demand_shift" or "supplier_quote"
    value: dict
    source: str  # the full text the model read
    quote: str  # the exact sentence the value comes from
    numbers: tuple[str, ...]  # every number the value depends on, as written in the quote


@dataclass
class Verdict:
    gate: str
    outcome: str
    reason: str = ""
    detail: dict = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.outcome == PASS


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def evidence(facts: list[Fact]) -> Verdict:
    bad = []
    for f in facts:
        if _norm(f.quote) not in _norm(f.source):
            bad.append(f"{f.kind}: quote not found in source")
            continue
        missing = [n for n in f.numbers if _norm(n) not in _norm(f.quote)]
        if missing:
            bad.append(f"{f.kind}: numbers {missing} not in quote")
            continue
        if f.kind == "demand_shift" and not 0.2 <= f.value.get("multiplier", 1.0) <= 5.0:
            bad.append("demand_shift: multiplier outside 0.2 to 5")
        if f.kind == "supplier_quote" and f.value.get("unit_price", 0) <= 0:
            bad.append("supplier_quote: price must be positive")
    if bad:
        return Verdict("evidence", REJECT, "; ".join(bad), {"rejected": bad})
    return Verdict("evidence", PASS, f"{len(facts)} facts tied to their sources")


def constraints(action: Action, state: State, business: BusinessPlan, suppliers: list[Supplier]) -> Verdict:
    by_id = {s.id: s for s in suppliers}
    problems = []
    for o in action.orders:
        s = by_id.get(o.supplier_id)
        if s is None:
            problems.append(f"unknown supplier {o.supplier_id}")
            continue
        if o.qty < s.moq:
            problems.append(f"{s.id}: {o.qty} below minimum {s.moq}")
        elif o.qty > s.capacity:
            problems.append(f"{s.id}: {o.qty} above capacity {s.capacity}")
        elif abs(o.unit_price - s.unit_price(o.qty)) > 1e-9 or abs(o.fixed_fee - s.fixed_fee) > 1e-9:
            problems.append(f"{s.id}: price does not match the supplier's tier")
    supplier_ids = set(by_id)
    for p in action.payouts:
        if p.purpose not in PAYOUT_PURPOSES:
            problems.append(f"payout to {p.receiver}: '{p.purpose}' is not an allowed Payouts purpose")
        if p.receiver in supplier_ids:
            problems.append(f"payout to supplier {p.receiver}: purchases must go through Orders, not Payouts")
        if p.amount <= 0:
            problems.append(f"payout to {p.receiver}: amount must be positive")
    spendable = state.cash + state.releases(state.week)
    after = spendable - action.spend
    if action.spend > spendable:
        problems.append(f"spend {action.spend:.2f} exceeds spendable cash {spendable:.2f} (held funds excluded)")
    elif after < business.cash_floor:
        problems.append(f"cash after spend {after:.2f} would fall below the floor {business.cash_floor:.2f}")
    if problems:
        code = "cash" if any("cash" in p for p in problems) else "rules"
        return Verdict("constraints", REJECT, "; ".join(problems), {"code": code, "problems": problems})
    return Verdict("constraints", PASS, f"spend {action.spend:.2f}, cash after {after:.2f}")


def envelope(action: Action, limits: Limits) -> Verdict:
    over = []
    if action.spend > limits.max_spend_per_week:
        over.append(f"spend {action.spend:.2f} over weekly limit {limits.max_spend_per_week:.2f}")
    for o in action.orders:
        if o.supplier_id not in limits.allowed_suppliers:
            over.append(f"supplier {o.supplier_id} not on the owner's list")
    if action.commission_rate is not None and not (
        limits.commission_min - 1e-9 <= action.commission_rate <= limits.commission_max + 1e-9
    ):
        over.append(f"commission {action.commission_rate:.2%} outside {limits.commission_min:.0%}-{limits.commission_max:.0%}")
    for p in action.payouts:
        if p.amount > limits.max_payout_per_affiliate:
            over.append(f"payout {p.amount:.2f} to {p.receiver} over the per-affiliate cap")
    if over:
        return Verdict("envelope", ESCALATE, "; ".join(over), {"items": over})
    return Verdict("envelope", PASS, "inside the owner's limits")


def stability(
    replan: Callable[[float], tuple[float, float]],
    rel_tol: float = 0.6,
    abs_tol: float = 120.0,
    commission_tol: float = 0.05,
) -> Verdict:
    """replan(scale) returns (units ordered this week, commission rate) with demand scaled by `scale`."""
    base_units, base_comm = replan(1.0)
    swings = []
    for scale in (0.95, 1.05):
        units, comm = replan(scale)
        du = abs(units - base_units)
        if du > abs_tol and du > rel_tol * max(base_units, 1.0):
            swings.append(f"a {abs(scale - 1):.0%} forecast nudge moves this week's order by {du:.0f} units")
        if abs(comm - base_comm) > commission_tol + 1e-6:
            swings.append(f"a {abs(scale - 1):.0%} forecast nudge moves commission by {abs(comm - base_comm):.1%}")
    if swings:
        return Verdict("stability", REJECT, "; ".join(swings), {"code": "unstable"})
    return Verdict("stability", PASS, "plan holds under a 5% forecast nudge")


@dataclass
class Imagined:
    cost: np.ndarray  # per run: tracking error plus lost sales and floor breaches, in dollars
    breach: np.ndarray  # per run: did cash dip below the floor
    inventory: np.ndarray  # runs x weeks
    cash: np.ndarray


def _rollout(twin: Twin, state: State, first: Action, fc: Forecast, business: BusinessPlan,
             weeks: int, runs: int, seed: int, lost_cost: float) -> Imagined:
    rng = np.random.default_rng(seed)
    n = min(weeks, len(fc.point))
    inv = np.zeros((runs, n))
    cash = np.zeros((runs, n))
    cost = np.zeros(runs)
    breach = np.zeros(runs, dtype=bool)
    sigma = (fc.hi - fc.lo) / (2 * 1.2816)  # an 80% band spans about +-1.28 sigma
    shocks = rng.standard_normal((runs, n))
    lift = twin.demand.elasticity * twin.demand.affiliate_share
    for r in range(runs):
        s = state.copy()
        c0 = s.commission_rate
        for t in range(n):
            a = first if t == 0 else Action(commission_rate=first.commission_rate)
            comm = a.commission_rate if a.commission_rate is not None else s.commission_rate
            d = max(0.0, (fc.point[t] + sigma[t] * shocks[r, t]) * (1 + lift * (comm - c0)))
            res = twin.step(s, a, demand=d)
            s = res.state
            inv[r, t], cash[r, t] = s.on_hand, s.cash
            wk = min(res.week + 1, len(business.inventory_target) - 1)
            cost[r] += abs(s.on_hand - business.inventory_target[wk]) * 1.0
            cost[r] += res.lost * lost_cost
            if s.cash < business.cash_floor:
                breach[r] = True
                cost[r] += (business.cash_floor - s.cash) * 0.5
    return Imagined(cost, breach, inv, cash)


def imagine(twin: Twin, state: State, action: Action, fc: Forecast, business: BusinessPlan,
            weeks: int = 6, runs: int = 200, max_breach: float = 0.05, seed: int = 11) -> tuple[Verdict, Imagined]:
    lost_cost = business.price * 0.25
    plan = _rollout(twin, state, action, fc, business, weeks, runs, seed, lost_cost)
    ghost = _rollout(twin, state, Action(), fc, business, weeks, runs, seed, lost_cost)  # same random draws
    gain = float(np.mean(ghost.cost - plan.cost))
    p_breach, g_breach = float(plan.breach.mean()), float(ghost.breach.mean())
    detail = {"expected_gain": gain, "p_breach": p_breach, "ghost_p_breach": g_breach,
              "beats_nothing_share": float(np.mean(plan.cost <= ghost.cost))}
    if p_breach > max(max_breach, g_breach):
        return Verdict("imagine", REJECT, f"cash floor breached in {p_breach:.0%} of imagined futures", {**detail, "code": "cash"}), ghost
    if action.orders and gain < 0:
        return Verdict("imagine", REJECT, f"plan does worse than doing nothing by {-gain:.0f} on average", {**detail, "code": "worse"}), ghost
    return Verdict("imagine", PASS, f"beats doing nothing by {gain:.0f} on average, floor risk {p_breach:.0%}", detail), ghost
