"""Monthly and annual planning: where the business stands against the budget, and the operating plan.

Two sets of numbers are kept apart, as finance teams do:
  * the budget: the owner's fixed annual plan, the accountability target;
  * the operating plan: monthly targets Helm proposes and the owner signs off, rebalanced
    each month so the full-year outlook returns to the budget where that is feasible.

Strategist (annual, at each month close): full-year outlook = year-to-date actuals plus a
forecast of the rest; it spreads the gap over the remaining months, capped by how much the
commission lever can actually move demand, so it never promises an impossible month.

Planner (monthly, at month start): the month's operating plan, with weekly sales targets
summed from days, a purchase budget and a commission budget that bound the weekly loop.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta

from helm.budget import AnnualBudget, revenue_bridge
from helm.calendar import WEEKDAY_PROFILE, month_key, split_exact
from helm.ledger import Ledger


@dataclass(frozen=True)
class Standing:
    """Budget versus actual at day, month and year level, as of the end of `through`."""

    through: str
    mtd_units: int
    mtd_units_budget: int
    mtd_revenue: int
    mtd_revenue_budget: int
    ytd_units: int
    ytd_units_budget: int
    ytd_revenue: int
    ytd_revenue_budget: int
    outlook_units: int  # year-to-date actual plus forecast for the rest of the year
    year_units_budget: int
    outlook_revenue: int
    year_revenue_budget: int
    bridge: dict  # year-to-date revenue gap split into volume and price

    def as_dict(self) -> dict:
        return asdict(self)


def standing(ledger: Ledger, budget: AnnualBudget, through: date, weekly_forecast: float, price_cents: int) -> Standing:
    cal = budget.cal
    days = [d for d in ledger.days() if cal.year_start <= d.day <= through]
    month_start = through.replace(day=1)
    mtd = [d for d in days if d.day >= month_start]
    ytd_b = budget.to_date(through)
    mtd_b = budget.to_date(through, start=month_start)
    year_b = budget.rollup("year")[f"{cal.year_start.year:04d}"]

    rest = [through + timedelta(days=i) for i in range(1, (cal.year_end - through).days + 1)]
    rest_units = round(sum(weekly_forecast / 7 * WEEKDAY_PROFILE[d.weekday()] for d in rest))
    ytd_units = sum(d.sold for d in days)
    ytd_revenue = sum(d.revenue for d in days)
    return Standing(
        through.isoformat(),
        sum(d.sold for d in mtd), mtd_b["units"], sum(d.revenue for d in mtd), mtd_b["revenue"],
        ytd_units, ytd_b["units"], ytd_revenue, ytd_b["revenue"],
        ytd_units + rest_units, year_b["units"], ytd_revenue + rest_units * price_cents, year_b["revenue"],
        revenue_bridge(ytd_units, ytd_revenue, ytd_b["units"], ytd_b["revenue"]),
    )


@dataclass(frozen=True)
class MonthPlan:
    month: str  # "2026-04"
    units: int  # operating sales target for the month
    budget_units: int  # what the fixed budget says
    weekly_units: dict  # ISO week key -> units, summed from the month's days (partial weeks included)
    purchase_budget: float  # dollars Helm may spend on stock this month without asking
    commission_budget: float  # dollars of commission the month may accrue
    rebalance_units: int  # how far this month moves from the budget to recover the year

    def as_dict(self) -> dict:
        return asdict(self)


def strategist(st: Standing, budget: AnnualBudget, today: date, max_lift: float) -> dict[str, int]:
    """Spread the full-year unit gap over the remaining months, capped by the achievable lift.

    max_lift is the largest fraction the commission lever can add to a month's demand.
    Returns month key -> operating unit target for every remaining month (this month included).
    """
    remaining = [k for k in budget.months if k >= month_key(today)]
    base = {k: budget.months[k].units for k in remaining}
    gap = st.year_units_budget - st.outlook_units  # positive: behind plan, needs more sales
    if not remaining:
        return {}
    weights = [base[k] for k in remaining]
    if gap > 0:
        caps = [int(base[k] * max_lift) for k in remaining]
        give = min(gap, sum(caps))
        parts = split_exact(give, weights)
        parts = [min(p, c) for p, c in zip(parts, caps)]
        return {k: base[k] + p for k, p in zip(remaining, parts)}
    # Ahead of plan: keep the budget. Helm does not throttle sales to hit a number from below.
    return dict(base)


def planner(month: str, units: int, budget: AnnualBudget, unit_cost: float, commission_rate: float,
            price_cents: int, slack: float = 1.25) -> MonthPlan:
    y, m = int(month[:4]), int(month[5:])
    days = budget.cal.month_days(y, m)
    per_day = split_exact(units, [WEEKDAY_PROFILE[d.weekday()] for d in days])
    weekly: dict[str, int] = {}
    for d, u in zip(days, per_day):
        iso = d.isocalendar()
        key = f"{iso.year:04d}-W{iso.week:02d}"
        weekly[key] = weekly.get(key, 0) + u
    line = budget.months[month]
    extra = units - line.units
    purchases = (line.purchases / 100 + max(0, extra) * unit_cost) * slack
    commission = units * price_cents / 100 * 0.4 * commission_rate * slack
    return MonthPlan(month, units, line.units, weekly, round(purchases, 2), round(commission, 2), extra)


def check_plan(plan: MonthPlan, opening_cash: float, cash_floor: float, low_units: int, price: float) -> list[str]:
    """The Validator for a month plan. Returns problems; empty means it passes."""
    problems = []
    if sum(plan.weekly_units.values()) != plan.units:
        problems.append("weekly targets do not add up to the month target")
    low_cash = opening_cash + low_units * price - plan.purchase_budget - plan.commission_budget
    if low_cash < cash_floor:
        problems.append(f"in a low-demand month cash would end at {low_cash:.0f}, under the floor {cash_floor:.0f}")
    if plan.purchase_budget <= 0:
        problems.append("purchase budget must be positive")
    return problems
