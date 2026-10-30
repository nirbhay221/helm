"""The business twin: a weekly simulation of a small online brand that sells through affiliates.

It is the world for the demo and the benchmark, and the Validator's Imagine gate uses
copies of it to run a proposed plan forward before any money moves.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from helm.model import Action, State


@dataclass(frozen=True)
class Shock:
    start_week: int
    weeks: int
    multiplier: float
    label: str


@dataclass
class DemandModel:
    base: float = 120.0
    season_amplitude: float = 0.15
    season_period: int = 52
    noise_cv: float = 0.12
    affiliate_share: float = 0.4  # share of sales that arrive through affiliates
    elasticity: float = 2.5  # extra demand per point of commission above the baseline rate
    baseline_commission: float = 0.10
    shocks: list[Shock] = field(default_factory=list)

    def expected(self, week: int, commission_rate: float) -> float:
        season = 1 + self.season_amplitude * np.sin(2 * np.pi * week / self.season_period)
        shock = 1.0
        for s in self.shocks:
            if s.start_week <= week < s.start_week + s.weeks:
                shock *= s.multiplier
        lift = 1 + self.elasticity * (commission_rate - self.baseline_commission) * self.affiliate_share
        return max(0.0, self.base * season * shock * lift)

    def sample(self, week: int, commission_rate: float, rng: np.random.Generator) -> float:
        mu = self.expected(week, commission_rate)
        return float(max(0.0, rng.normal(mu, self.noise_cv * mu)))


@dataclass(frozen=True)
class HoldRule:
    """PayPal may hold part of a sales spike for review (its funds-availability page names spikes)."""

    spike_ratio: float = 1.8
    hold_fraction: float = 0.3
    hold_weeks: int = 3


@dataclass
class WeekResult:
    week: int
    demand: float
    sales: float
    lost: float
    revenue: float
    held_now: float
    spend: float
    commission_paid: float
    state: State


class Twin:
    def __init__(
        self,
        demand: DemandModel,
        price: float,
        lead_times: dict[str, int],
        hold: HoldRule | None = None,
        seed: int = 0,
    ):
        self.demand = demand
        self.price = price
        self.lead_times = lead_times
        self.hold = hold or HoldRule()
        self.rng = np.random.default_rng(seed)

    def step(self, state: State, action: Action, demand: float | None = None) -> WeekResult:
        s = state.copy()
        w = s.week
        if action.commission_rate is not None:
            s.commission_rate = action.commission_rate

        # Orders placed this week are paid now and arrive after the supplier's lead time.
        for o in action.orders:
            s.cash -= o.cost
            s.pipeline.append((w + max(1, self._lead(o.supplier_id)), float(o.qty), o.supplier_id))
        s.cash -= sum(p.amount for p in action.payouts)

        s.on_hand += s.arrivals(w)
        s.pipeline = [p for p in s.pipeline if p[0] != w]
        s.cash += s.releases(w)
        s.held = [h for h in s.held if h[0] != w]

        d = demand if demand is not None else self.demand.sample(w, s.commission_rate, self.rng)
        sales = min(d, s.on_hand)
        s.on_hand -= sales
        revenue = sales * self.price

        trailing = s.revenue_history[-4:]
        held_now = 0.0
        if trailing and revenue > self.hold.spike_ratio * (sum(trailing) / len(trailing)):
            held_now = revenue * self.hold.hold_fraction
            s.held.append((w + self.hold.hold_weeks, held_now))
        commission = s.commission_rate * revenue * self.demand.affiliate_share
        s.cash += revenue - held_now - commission

        s.demand_history.append(d)
        s.revenue_history.append(revenue)
        s.week += 1
        return WeekResult(w, d, sales, d - sales, revenue, held_now, action.spend, commission, s)

    def _lead(self, supplier_id: str) -> int:
        return self.lead_times.get(supplier_id, 1)
