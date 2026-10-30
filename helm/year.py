"""A full fiscal year of the demo business: daily world, annual budget, and the weekly plan derived from it."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from helm.budget import AnnualBudget, MonthLine
from helm.calendar import FiscalCalendar, week_start
from helm.model import BusinessPlan, Limits, Order
from helm.scenario import SUPPLIERS
from helm.sim.world import DailyDemand, DailyWorld, DatedShock, cents

PRICE_CENTS = 2400
PLANNED_UNIT_COST = 7.60
COVER_WEEKS = 3
CASH_FLOOR = 1500.0


@dataclass
class Year:
    cal: FiscalCalendar
    world: DailyWorld
    budget: AnnualBudget
    plan: BusinessPlan  # weekly targets for the Navigator, read off the daily budget
    limits: Limits
    origin: date  # Monday that week index 0 refers to, for both the weekly plan and the weekly state
    affiliates: dict[str, float] = field(default_factory=dict)  # receiver -> share of affiliate sales


def build_year(year: int = 2026, seed: int = 7, viral: date | None = date(2026, 3, 9),
               viral_days: int = 21, viral_multiplier: float = 3.0, history_days: int = 84) -> Year:
    cal = FiscalCalendar.calendar_year(year)
    shocks = [DatedShock(viral, viral_days, viral_multiplier, "creator video goes viral")] if viral else []
    world = DailyWorld(list(SUPPLIERS), PRICE_CENTS, DailyDemand(shocks=shocks), seed=seed)

    # Twelve weeks before Helm takes over, run the way the owner ran it: top up from Harbor every Monday.
    start = cal.year_start - timedelta(days=history_days)
    world.open(start, stock=360, cash_cents=600_000)
    harbor = next(s for s in SUPPLIERS if s.id == "harborwhole")
    d = start
    while d < cal.year_start:
        if d.weekday() == 0:
            need = 3 * 120 - world.stock() - sum(u for _, u, _ in world.pipeline)
            if need > 0:
                q = max(need, harbor.moq)
                world.place_order(d, Order(harbor.id, q, harbor.unit_price(q), harbor.fixed_fee), key=f"hist:{d}")
            if world.commission_owed:
                from helm.model import Payout
                world.pay(d, Payout("affiliates", world.commission_owed / 100, "commission"), key=f"hist-pay:{d}")
        world.run_day(d)
        d += timedelta(days=1)

    budget = _budget(cal, world)
    origin = week_start(start)
    plan = _weekly_plan(budget, origin)
    limits = Limits(max_spend_per_week=9000.0, commission_min=0.05, commission_max=0.25,
                    allowed_suppliers=frozenset(s.id for s in SUPPLIERS))
    affiliates = {"@pawsandprints": 0.5, "@tailwagtips": 0.3, "@dogdadreviews": 0.2}
    return Year(cal, world, budget, plan, limits, origin, affiliates)


def _budget(cal: FiscalCalendar, world: DailyWorld) -> AnnualBudget:
    calm = DailyDemand()  # the budget is made before anyone knows about the viral video
    months: dict[str, MonthLine] = {}
    stock, cash = world.stock(), world.cash()
    for (y, m) in cal.months():
        days = cal.month_days(y, m)
        units = round(sum(calm.expected(d, calm.baseline_commission) for d in days))
        revenue = units * PRICE_CENTS
        commission = round(revenue * calm.affiliate_share * calm.baseline_commission)
        next_week = sum(calm.expected(days[-1] + timedelta(days=i), calm.baseline_commission) for i in range(1, 8))
        stock_end = round(COVER_WEEKS * next_week)
        bought = units + stock_end - stock
        purchases = cents(bought * PLANNED_UNIT_COST)
        cash_end = cash + revenue - purchases - commission
        months[f"{y:04d}-{m:02d}"] = MonthLine(units, revenue, purchases, commission, stock_end, cash_end)
        stock, cash = stock_end, cash_end
    return AnnualBudget(cal, months, world.stock(), world.cash())


def _weekly_plan(budget: AnnualBudget, origin: date) -> BusinessPlan:
    """Week k's target is the budget position at the start of week k (end of the day before its Monday)."""
    inv, cash, sales = [], [], []
    cal = budget.cal
    for k in range(80):
        monday = origin + timedelta(days=7 * k)
        week = [monday + timedelta(days=i) for i in range(7)]
        sales.append(float(sum(budget.day(d).units if cal.year_start <= d <= cal.year_end else 120 / 7 for d in week)))
        eod = origin + timedelta(days=7 * k - 1)
        if eod < cal.year_start:
            inv.append(float(budget.opening_stock))
            cash.append(budget.opening_cash / 100)
        else:
            t = budget.day(min(eod, cal.year_end))
            inv.append(float(t.stock_end))
            cash.append(t.cash_end / 100)
    return BusinessPlan(tuple(inv), tuple(cash), cash_floor=CASH_FLOOR, price=PRICE_CENTS / 100, sales_target=tuple(sales))


def runtime(y: Year, imagine_runs: int = 100):
    """Wire a Year into the LangGraph runtime: the producer/validator brain plus the daily world."""
    from helm.graph import Runtime
    from helm.loop import Helm
    from helm.sim.twin import DemandModel, Twin

    validator_twin = Twin(DemandModel(base=120.0, elasticity=y.world.demand.elasticity), PRICE_CENTS / 100, {s.id: s.lead_weeks for s in SUPPLIERS})
    brain = Helm(validator_twin, y.plan, y.limits, list(SUPPLIERS), imagine_runs=imagine_runs)
    return Runtime(y.world, brain, y.origin, y.affiliates, budget=y.budget, base_plan=y.plan)


def run_days(y: Year, app, rt, start: date, end: date, thread_id: str, owner=None) -> list[dict]:
    """Drive the world day by day; on each Monday run the weekly graph first."""
    from helm.graph import run_week

    journal = []
    d = start
    while d <= end:
        if d.weekday() == 0:
            out = run_week(app, d, thread_id, owner)
            if "__interrupt__" in out:
                return journal + [{"paused": out["__interrupt__"][0].value}]
            journal.append(out["journal"])
        y.world.run_day(d)
        d += timedelta(days=1)
    return journal


def run_year_days(y: Year, app, start: date, end: date, thread_id: str, owner=None) -> list[dict]:
    """Drive the world day by day through the parent day graph (monthly and weekly levels as subgraphs)."""
    from helm.graph import run_day

    out = []
    d = start
    while d <= end:
        res = run_day(app, d, thread_id, owner)
        if "__interrupt__" in res:
            return out + [{"day": d.isoformat(), "paused": res["__interrupt__"][0].value}]
        if res.get("ran"):
            out.append({"day": d.isoformat(), "ran": res["ran"], "month": res.get("month"), "week": res.get("week")})
        y.world.run_day(d)
        d += timedelta(days=1)
    return out
