"""Synthetic single-product business: Helm's environment.

The business holds inventory and cash. Each period:
  1. any supplier order placed `lead_time` periods ago arrives (adds inventory),
  2. demand is realized (baseline forecast + noise + any injected shock),
  3. sales = min(demand, inventory); revenue moves cash in,
  4. the supplier order placed this period is paid for now (cash out).

The "plan" is the baseline demand forecast and a target inventory level. The
forecast deliberately does NOT know about shocks, so when a shock hits, actual
inventory and cash drift away from plan and the controller has to react to the
realized state. That drift is the variance Helm exists to close.

Nothing here is random-at-runtime beyond a seeded RNG, so runs are reproducible.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class BusinessParams:
    price: float = 20.0            # revenue per unit sold
    unit_cost: float = 8.0         # cost per unit ordered (paid at order time)
    lead_time: int = 1             # periods between placing an order and arrival
    init_inventory: float = 120.0
    init_cash: float = 2000.0
    target_inventory: float = 120.0
    cash_floor: float = 0.0
    baseline_demand: float = 40.0
    demand_noise_sd: float = 4.0
    # If set, actual demand replays this recorded series (period t -> value) instead
    # of baseline + gaussian noise. Lets the sim run on real, non-synthetic demand.
    demand_series: list[float] | None = None


@dataclass
class Observation:
    period: int
    forecast_demand: float
    demand: float
    sales: float
    inventory: float
    cash: float
    order_placed: float
    order_arrived: float
    target_inventory: float

    @property
    def inv_deviation(self) -> float:
        return abs(self.inventory - self.target_inventory)


class BusinessSim:
    def __init__(
        self,
        params: BusinessParams | None = None,
        seed: int = 7,
        n_periods: int = 24,
    ) -> None:
        self.p = params or BusinessParams()
        self.n_periods = n_periods
        self.rng = np.random.default_rng(seed)
        self.t = 0
        self.inventory = float(self.p.init_inventory)
        self.cash = float(self.p.init_cash)
        self._pipeline: dict[int, float] = {}   # arrival_period -> qty
        self._shocks: dict[int, float] = {}      # period -> additive demand delta
        self.history: list[Observation] = []

    # --- plan / forecast ----------------------------------------------------
    def forecast(self, horizon: int) -> np.ndarray:
        """Planned demand for the next `horizon` periods (baseline, shock-blind)."""
        return np.full(horizon, self.p.baseline_demand, dtype=float)

    def target_trajectory(self, horizon_plus_one: int) -> np.ndarray:
        return np.full(horizon_plus_one, self.p.target_inventory, dtype=float)

    def pipeline_arrivals(self, horizon: int) -> dict[int, float]:
        """Already-placed orders that will arrive within the horizon, as
        {offset_from_now: qty}. Lets the controller account for in-flight stock."""
        out: dict[int, float] = {}
        for arrival_t, qty in self._pipeline.items():
            offset = arrival_t - self.t
            if 0 <= offset < horizon:
                out[offset] = out.get(offset, 0.0) + qty
        return out

    def inject_shock(self, period: int, demand_delta: float) -> None:
        self._shocks[period] = demand_delta

    # --- dynamics -----------------------------------------------------------
    def done(self) -> bool:
        return self.t >= self.n_periods

    def step(self, order_qty: float, order_cost: float | None = None) -> Observation:
        """Advance one period. `order_qty` is this period's supplier order.

        `order_cost`, if given, is the actual amount paid for that order (as
        computed by the buying arm from real supplier quotes). If omitted, the
        order is costed at the flat ``unit_cost`` (used by the standalone
        controller demo and tests)."""
        order_qty = max(0.0, float(order_qty))

        # 1. arrivals scheduled for now
        arrived = self._pipeline.pop(self.t, 0.0)
        self.inventory += arrived

        # 2. realize demand: replay a real recorded series if given, else
        #    synthesize it as baseline + gaussian noise. Injected shocks (if any)
        #    add on top of either.
        if self.p.demand_series is not None and self.t < len(self.p.demand_series):
            demand = float(self.p.demand_series[self.t]) + self._shocks.get(self.t, 0.0)
        else:
            noise = float(self.rng.normal(0.0, self.p.demand_noise_sd))
            demand = self.p.baseline_demand + noise + self._shocks.get(self.t, 0.0)
        demand = max(0.0, demand)

        # 3. sales and revenue
        sales = min(demand, self.inventory)
        self.inventory -= sales
        self.cash += self.p.price * sales

        # 4. place + pay for this period's order; schedule its arrival
        if order_qty > 0:
            cost = self.p.unit_cost * order_qty if order_cost is None else float(order_cost)
            self.cash -= cost
            self._pipeline[self.t + self.p.lead_time] = (
                self._pipeline.get(self.t + self.p.lead_time, 0.0) + order_qty
            )

        obs = Observation(
            period=self.t,
            forecast_demand=self.p.baseline_demand,
            demand=round(demand, 2),
            sales=round(sales, 2),
            inventory=round(self.inventory, 2),
            cash=round(self.cash, 2),
            order_placed=round(order_qty, 2),
            order_arrived=round(arrived, 2),
            target_inventory=self.p.target_inventory,
        )
        self.history.append(obs)
        self.t += 1
        return obs

    # --- reporting ----------------------------------------------------------
    def cumulative_inv_deviation(self) -> float:
        return round(sum(o.inv_deviation for o in self.history), 2)

    def min_cash(self) -> float:
        return round(min((o.cash for o in self.history), default=self.cash), 2)
