"""A creator-marketplace treasury simulator.

Each period:
  1. buyers pay for creator sales (GMV). The platform collects it (money in),
     keeps a take rate as revenue, and owes the rest to creators.
  2. refunds land immediately; chargebacks land after a lag (card rules expose a
     sale to clawback for roughly 120 days), both drawn from cash.
  3. the controller decides a total payout to creators this period; it is capped
     at what is owed and at cash on hand, and pays down the oldest creator
     balances first (so the waiting metric is real).
  4. the platform must keep a rolling reserve against the sales still exposed to
     chargebacks, and cash above a floor.

Nothing here is random at runtime beyond a seeded RNG, so runs reproduce. The
owed balances are tracked as aged lots (a FIFO queue), so "how long creators
waited to be paid" is measured, not assumed.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import numpy as np


@dataclass
class MarketplaceParams:
    baseline_gmv: float = 1000.0      # expected gross merchandise value per period
    take_rate: float = 0.20           # platform keeps this; creators get the rest
    refund_rate: float = 0.05         # fraction of GMV refunded immediately
    chargeback_rate: float = 0.03     # fraction of GMV charged back, after a lag
    chargeback_lag: int = 2           # periods until a chargeback lands
    chargeback_window: int = 4        # periods a sale stays exposed to clawback
    reserve_rate: float = 0.30        # reserve to hold against exposed GMV
    cash_floor: float = 0.0           # cash must not go below this
    init_cash: float = 1500.0
    gmv_noise_sd: float = 60.0
    demand_series: list[float] | None = None   # real GMV path, if given


@dataclass
class MarketObservation:
    period: int
    gmv: float                        # realized gross merchandise value
    forecast_gmv: float               # what the plan expected
    creator_earnings: float           # owed to creators from this period
    refunds: float
    chargebacks: float
    payout: float                     # paid to creators this period
    cash: float
    owed: float                       # total still owed to creators
    oldest_wait: int                  # periods the oldest unpaid balance has waited
    exposure: float                   # GMV still within the chargeback window
    reserve_required: float
    cash_floor_ok: bool               # cash >= floor
    reserve_ok: bool                  # cash - reserve_required >= floor


class CreatorMarketplace:
    def __init__(self, params: MarketplaceParams | None = None, seed: int = 7,
                 n_periods: int = 24) -> None:
        self.p = params or MarketplaceParams()
        self.n_periods = n_periods
        self.rng = np.random.default_rng(seed)
        self.t = 0
        self.cash = float(self.p.init_cash)
        # owed to creators as aged lots: deque of [amount, age_in_periods]
        self._owed_lots: deque[list] = deque()
        self._gmv_history: list[float] = []     # realized GMV per past period
        self._pending_cb: dict[int, float] = {}  # period -> chargeback amount landing
        self.history: list[MarketObservation] = []

    # --- plan / forecast ----------------------------------------------------
    def forecast_gmv(self, horizon: int) -> np.ndarray:
        return np.full(horizon, self.p.baseline_gmv, dtype=float)

    @property
    def owed(self) -> float:
        return float(sum(lot[0] for lot in self._owed_lots))

    def exposure(self) -> float:
        """GMV from the last `chargeback_window` periods still exposed to clawback."""
        w = self.p.chargeback_window
        return float(sum(self._gmv_history[-w:])) if self._gmv_history else 0.0

    def reserve_required(self) -> float:
        return self.p.reserve_rate * self.exposure()

    def payable_now(self) -> float:
        """Cash the controller may pay out without breaching floor+reserve."""
        return max(0.0, self.cash - self.p.cash_floor - self.reserve_required())

    def done(self) -> bool:
        return self.t >= self.n_periods

    # --- dynamics -----------------------------------------------------------
    def _realize_gmv(self) -> float:
        if self.p.demand_series is not None and self.t < len(self.p.demand_series):
            return max(0.0, float(self.p.demand_series[self.t]))
        noise = float(self.rng.normal(0.0, self.p.gmv_noise_sd))
        return max(0.0, self.p.baseline_gmv + noise)

    def _pay_down(self, amount: float) -> int:
        """Pay `amount` against the oldest owed lots first. Returns the age of the
        oldest lot that received payment (the longest wait cleared this period)."""
        remaining = amount
        oldest_paid_age = 0
        while remaining > 1e-9 and self._owed_lots:
            lot = self._owed_lots[0]
            oldest_paid_age = max(oldest_paid_age, int(lot[1]))
            if lot[0] <= remaining + 1e-9:
                remaining -= lot[0]
                self._owed_lots.popleft()
            else:
                lot[0] -= remaining
                remaining = 0.0
        return oldest_paid_age

    def step(self, payout: float) -> MarketObservation:
        """Advance one period. `payout` is the total the controller pays creators
        now; it is clamped to what is owed and to cash on hand."""
        p = self.p
        forecast = p.baseline_gmv

        # 1. GMV collected; creators accrue earnings
        gmv = self._realize_gmv()
        self._gmv_history.append(gmv)
        self.cash += gmv
        earnings = (1.0 - p.take_rate) * gmv
        if earnings > 1e-9:
            self._owed_lots.append([earnings, 0])

        # 2. refunds now, chargebacks after a lag
        refunds = p.refund_rate * gmv
        self.cash -= refunds
        cb_future = p.chargeback_rate * gmv
        if cb_future > 1e-9:
            land = self.t + p.chargeback_lag
            self._pending_cb[land] = self._pending_cb.get(land, 0.0) + cb_future
        chargebacks = self._pending_cb.pop(self.t, 0.0)
        self.cash -= chargebacks

        # 3. payout to creators, clamped to owed and to cash on hand
        payout = max(0.0, float(payout))
        payout = min(payout, self.owed, max(0.0, self.cash))
        oldest_wait_before = max((int(lot[1]) for lot in self._owed_lots), default=0)
        self._pay_down(payout)
        self.cash -= payout

        # 4. age the still-unpaid balances
        for lot in self._owed_lots:
            lot[1] += 1

        exposure = self.exposure()
        reserve_required = p.reserve_rate * exposure
        obs = MarketObservation(
            period=self.t, gmv=round(gmv, 2), forecast_gmv=round(forecast, 2),
            creator_earnings=round(earnings, 2), refunds=round(refunds, 2),
            chargebacks=round(chargebacks, 2), payout=round(payout, 2),
            cash=round(self.cash, 2), owed=round(self.owed, 2),
            oldest_wait=oldest_wait_before, exposure=round(exposure, 2),
            reserve_required=round(reserve_required, 2),
            cash_floor_ok=self.cash >= p.cash_floor - 1e-6,
            reserve_ok=self.cash - reserve_required >= p.cash_floor - 1e-6,
        )
        self.history.append(obs)
        self.t += 1
        return obs
