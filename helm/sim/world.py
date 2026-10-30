"""The daily business world: the source of truth for the demo, written entirely to the ledger.

Customers arrive every day (integer units, weekday pattern, season, shocks, and a lift from
the affiliate commission rate). PayPal holds part of a revenue spike and releases it on a
real date. Supplier orders arrive on real dates. Commission accrues daily and is owed until
Helm pays it through a Payouts batch.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np

from helm.calendar import WEEKDAY_PROFILE, week_start
from helm.ledger import Event, Ledger
from helm.model import Order, Payout, State, Supplier


@dataclass(frozen=True)
class DatedShock:
    start: date
    days: int
    multiplier: float
    label: str


@dataclass
class DailyDemand:
    weekly_base: float = 120.0
    season_amplitude: float = 0.15
    affiliate_share: float = 0.4
    elasticity: float = 1.0  # +0.4% demand per commission point: worth raising only when stock is high
    baseline_commission: float = 0.10
    shocks: list[DatedShock] = field(default_factory=list)

    def expected(self, d: date, commission_rate: float) -> float:
        season = 1 + self.season_amplitude * np.sin(2 * np.pi * d.timetuple().tm_yday / 365.25)
        shock = 1.0
        for s in self.shocks:
            if s.start <= d < s.start + timedelta(days=s.days):
                shock *= s.multiplier
        lift = 1 + self.elasticity * (commission_rate - self.baseline_commission) * self.affiliate_share
        return max(0.0, self.weekly_base / 7 * WEEKDAY_PROFILE[d.weekday()] * season * shock * lift)


@dataclass(frozen=True)
class DailyHoldRule:
    spike_ratio: float = 1.8  # a day's revenue above this multiple of the trailing 28-day average
    hold_fraction: float = 0.3
    hold_days: int = 21


def cents(dollars: float) -> int:
    return int(round(dollars * 100))


@dataclass
class DailyWorld:
    suppliers: list[Supplier]
    price_cents: int
    demand: DailyDemand
    ledger: Ledger = field(default_factory=Ledger)
    hold: DailyHoldRule = field(default_factory=DailyHoldRule)
    commission_rate: float = 0.10
    seed: int = 0
    pipeline: list[tuple[date, int, str]] = field(default_factory=list)  # (arrival day, units, supplier)
    holds: list[tuple[date, int]] = field(default_factory=list)  # (release day, cents)
    commission_owed: int = 0
    today: date | None = None

    def __post_init__(self):
        self.rng = np.random.default_rng(self.seed)
        self._by_id = {s.id: s for s in self.suppliers}

    def open(self, day: date, stock: int, cash_cents: int) -> None:
        self.ledger.append(Event(day, "opening", units=stock, cents=cash_cents))
        self.today = day

    # ---- actions (called by an executor) -------------------------------------------------
    def place_order(self, day: date, order: Order, key: str, paypal_id: str = "") -> bool:
        cost = cents(order.qty * order.unit_price) + cents(order.fixed_fee)
        ok = self.ledger.append(Event(day, "purchase", units=order.qty, cents=cost, ref=order.supplier_id,
                                      paypal_id=paypal_id, idempotency_key=key))
        if ok:
            lead = self._by_id[order.supplier_id].lead_weeks
            self.pipeline.append((day + timedelta(days=7 * lead), order.qty, order.supplier_id))
        return ok

    def pay(self, day: date, payout: Payout, key: str, paypal_id: str = "") -> bool:
        amount = cents(payout.amount)
        ok = self.ledger.append(Event(day, "payout", cents=amount, ref=payout.receiver,
                                      paypal_id=paypal_id, idempotency_key=key))
        if ok:
            self.commission_owed -= amount
        return ok

    def set_commission(self, rate: float) -> None:
        self.commission_rate = rate

    # ---- one day of business ---------------------------------------------------------------
    def run_day(self, day: date) -> None:
        for arrival, units, sup in [p for p in self.pipeline if p[0] == day]:
            self.ledger.append(Event(day, "arrival", units=units, ref=sup))
        self.pipeline = [p for p in self.pipeline if p[0] != day]
        for release, amount in [h for h in self.holds if h[0] == day]:
            self.ledger.append(Event(day, "release", cents=amount))
        self.holds = [h for h in self.holds if h[0] != day]

        stock = self.stock()
        wanted = int(self.rng.poisson(self.demand.expected(day, self.commission_rate)))
        sold = min(wanted, stock)
        revenue = sold * self.price_cents
        self.ledger.append(Event(day, "demand", units=wanted))
        self.ledger.append(Event(day, "sale", units=sold, cents=revenue))

        recent = [d.revenue for d in self.ledger.days()[-29:-1]]
        if len(recent) >= 7 and revenue > self.hold.spike_ratio * (sum(recent) / len(recent)):
            held = int(revenue * self.hold.hold_fraction)
            release = day + timedelta(days=self.hold.hold_days)
            self.ledger.append(Event(day, "hold", cents=held, release_on=release))
            self.holds.append((release, held))

        commission = int(round(revenue * self.demand.affiliate_share * self.commission_rate))
        if commission:
            self.ledger.append(Event(day, "commission", cents=commission))
            self.commission_owed += commission
        self.today = day + timedelta(days=1)

    # ---- views ---------------------------------------------------------------------------------
    def stock(self) -> int:
        days = self.ledger.days()
        return days[-1].stock_end if days else 0

    def cash(self) -> int:
        days = self.ledger.days()
        return days[-1].cash_end if days else 0

    def weekly_state(self, monday: date, first_monday: date) -> State:
        """The view the weekly Navigator plans on: whole past weeks, in week indices from `first_monday`."""
        def idx(d: date) -> int:
            return (week_start(d) - first_monday).days // 7

        weekly_demand: dict[int, int] = {}
        weekly_revenue: dict[int, int] = {}
        for d in self.ledger.days():
            if d.day < monday:
                weekly_demand[idx(d.day)] = weekly_demand.get(idx(d.day), 0) + d.demand
                weekly_revenue[idx(d.day)] = weekly_revenue.get(idx(d.day), 0) + d.revenue
        weeks = sorted(k for k in weekly_demand if k < idx(monday))
        full = [k for k in weeks if k > weeks[0]] if len(weeks) > 1 else weeks  # drop a partial first week
        return State(
            week=idx(monday),
            on_hand=float(self.stock()),
            cash=self.cash() / 100,
            commission_rate=self.commission_rate,
            pipeline=[(idx(a), float(u), s) for a, u, s in self.pipeline],
            held=[(idx(r), c / 100) for r, c in self.holds],
            demand_history=[float(weekly_demand[k]) for k in full],
            revenue_history=[weekly_revenue[k] / 100 for k in full],
        )
