"""Fiscal calendar: real dates, calendar months, Monday-to-Sunday weeks.

Every total Helm reports is summed from days, so a week that spans two months is split
by day and month-to-date figures are exact.
"""

from __future__ import annotations

import calendar as _cal
from dataclasses import dataclass
from datetime import date, timedelta

# Share of a week's demand that lands on each weekday (Mon..Sun). Mean is exactly 1.
WEEKDAY_PROFILE = (0.92, 0.95, 0.98, 1.00, 1.08, 1.12, 0.95)


@dataclass(frozen=True)
class FiscalCalendar:
    year_start: date  # first day of the fiscal year (1 Jan by default)

    @classmethod
    def calendar_year(cls, year: int) -> "FiscalCalendar":
        return cls(date(year, 1, 1))

    @property
    def year_end(self) -> date:
        return date(self.year_start.year + 1, self.year_start.month, self.year_start.day) - timedelta(days=1)

    def days(self) -> list[date]:
        n = (self.year_end - self.year_start).days + 1
        return [self.year_start + timedelta(days=i) for i in range(n)]

    def months(self) -> list[tuple[int, int]]:
        out, d = [], self.year_start.replace(day=1)
        while d <= self.year_end:
            out.append((d.year, d.month))
            d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
        return out

    def month_days(self, year: int, month: int) -> list[date]:
        n = _cal.monthrange(year, month)[1]
        return [date(year, month, i) for i in range(1, n + 1)]


def month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def week_key(d: date) -> str:
    iso = d.isocalendar()
    return f"{iso.year:04d}-W{iso.week:02d}"


def week_days(monday: date) -> list[date]:
    return [monday + timedelta(days=i) for i in range(7)]


def split_exact(total: int, weights: list[float]) -> list[int]:
    """Split an integer total by weights so the parts sum exactly to the total (largest remainder)."""
    if not weights:
        return []
    s = sum(weights)
    raw = [total * w / s for w in weights]
    parts = [int(x // 1) for x in raw]
    short = total - sum(parts)
    order = sorted(range(len(raw)), key=lambda i: raw[i] - parts[i], reverse=True)
    for i in order[:short]:
        parts[i] += 1
    return parts
