"""The owner's annual budget and the variance views Helm steers by.

The budget is a fixed accountability target, set by month and spread down to each day by
the weekday profile, with exact integer splitting so days add up to months to the cent.
Week, month and year budgets are summed from those days, the same way actuals are, so a
budget-versus-actual comparison is like for like at every level.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from helm.calendar import WEEKDAY_PROFILE, FiscalCalendar, month_key, split_exact, week_key


@dataclass(frozen=True)
class MonthLine:
    units: int  # units sold
    revenue: int  # cents
    purchases: int  # cents spent on stock
    commission: int  # cents of affiliate commission
    stock_end: int  # units on hand at month end
    cash_end: int  # spendable cents at month end


@dataclass(frozen=True)
class DayTarget:
    day: date
    units: int
    revenue: int
    purchases: int
    commission: int
    stock_end: int
    cash_end: int


FLOW_FIELDS = ("units", "revenue", "purchases", "commission")
STOCK_FIELDS = ("stock_end", "cash_end")


@dataclass
class AnnualBudget:
    cal: FiscalCalendar
    months: dict[str, MonthLine]  # "2026-03" -> line
    opening_stock: int
    opening_cash: int

    def __post_init__(self):
        expected = [f"{y:04d}-{m:02d}" for y, m in self.cal.months()]
        if list(self.months) != expected:
            raise ValueError("budget needs one line per fiscal month, in order")
        self._days = self._spread()

    def _spread(self) -> list[DayTarget]:
        out: list[DayTarget] = []
        prev_stock, prev_cash = self.opening_stock, self.opening_cash
        for (y, m) in self.cal.months():
            line = self.months[f"{y:04d}-{m:02d}"]
            days = self.cal.month_days(y, m)
            w = [WEEKDAY_PROFILE[d.weekday()] for d in days]
            flows = {f: split_exact(getattr(line, f), w) for f in FLOW_FIELDS}
            n = len(days)
            for i, d in enumerate(days):
                frac = (i + 1) / n
                out.append(DayTarget(
                    d, flows["units"][i], flows["revenue"][i], flows["purchases"][i], flows["commission"][i],
                    round(prev_stock + (line.stock_end - prev_stock) * frac),
                    round(prev_cash + (line.cash_end - prev_cash) * frac),
                ))
            prev_stock, prev_cash = line.stock_end, line.cash_end
        return out

    def days(self) -> list[DayTarget]:
        return self._days

    def day(self, d: date) -> DayTarget:
        return self._days[(d - self.cal.year_start).days]

    def rollup(self, level: str) -> dict[str, dict[str, int]]:
        keyf = {"week": week_key, "month": month_key, "year": lambda d: f"{d.year:04d}"}[level]
        out: dict[str, dict[str, int]] = defaultdict(lambda: {f: 0 for f in FLOW_FIELDS})
        for t in self._days:
            row = out[keyf(t.day)]
            for f in FLOW_FIELDS:
                row[f] += getattr(t, f)
            for s in STOCK_FIELDS:
                row[s] = getattr(t, s)
        return dict(out)

    def to_date(self, through: date, start: date | None = None) -> dict[str, int]:
        """Budget flows summed from `start` (default: year start) through `through`, inclusive."""
        start = start or self.cal.year_start
        row = {f: 0 for f in FLOW_FIELDS}
        for t in self._days:
            if start <= t.day <= through:
                for f in FLOW_FIELDS:
                    row[f] += getattr(t, f)
        return row


@dataclass(frozen=True)
class Variance:
    level: str  # "week", "month", "year"
    key: str
    actual: dict[str, int]
    budget: dict[str, int]

    def gap(self, field: str) -> int:
        return self.actual.get(field, 0) - self.budget.get(field, 0)

    def pct(self, field: str) -> float:
        b = self.budget.get(field, 0)
        return self.gap(field) / b if b else 0.0


def revenue_bridge(actual_units: int, actual_revenue: int, budget_units: int, budget_revenue: int) -> dict[str, int]:
    """Split a revenue gap into a volume effect and a price effect (standard price-volume bridge).

    volume = (actual units - budget units) x budget price; price = (actual price - budget price) x actual units.
    The two add up exactly to the revenue gap.
    """
    budget_price = budget_revenue / budget_units if budget_units else 0.0
    volume = round((actual_units - budget_units) * budget_price)
    price = (actual_revenue - budget_revenue) - volume
    return {"volume": volume, "price": price, "total": actual_revenue - budget_revenue}
