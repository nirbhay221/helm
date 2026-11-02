"""Payout policies and a runner, to compare Helm against the naive extremes.

The point of the comparison is the real tension creators face: pay everyone the
moment money arrives and you can breach the reserve you owe against chargebacks
(and your cash floor); batch payouts monthly and you are safe but creators wait.
Helm's controller aims to pay as fast as solvency and reserve allow, getting the
low wait of the eager policy with the safety of the cautious one.
"""
from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Callable

from .controller import CashPayoutController
from .sim import CreatorMarketplace

Policy = Callable[[CreatorMarketplace], float]


@dataclass
class MarketplaceMetrics:
    avg_wait: float            # mean periods the oldest unpaid balance waited
    max_wait: int              # worst wait any creator balance saw
    avg_owed: float            # mean outstanding owed to creators
    total_paid: float
    final_owed: float
    cash_floor_breaches: int   # periods cash fell below the floor
    reserve_breaches: int      # periods cash could not cover floor + required reserve
    reserve_shortfall: float   # total $ by which cash fell short of floor+reserve, summed

    @staticmethod
    def from_history(sim: CreatorMarketplace) -> "MarketplaceMetrics":
        h = sim.history
        floor = sim.p.cash_floor
        shortfall = sum(max(0.0, (floor + o.reserve_required) - o.cash) for o in h)
        return MarketplaceMetrics(
            avg_wait=round(mean(o.oldest_wait for o in h), 2) if h else 0.0,
            max_wait=max((o.oldest_wait for o in h), default=0),
            avg_owed=round(mean(o.owed for o in h), 2) if h else 0.0,
            total_paid=round(sum(o.payout for o in h), 2),
            final_owed=round(h[-1].owed, 2) if h else 0.0,
            cash_floor_breaches=sum(1 for o in h if not o.cash_floor_ok),
            reserve_breaches=sum(1 for o in h if not o.reserve_ok),
            reserve_shortfall=round(shortfall, 2),
        )


def pay_all_now_policy() -> Policy:
    """Pay creators everything owed, immediately. Fast, but blind to the reserve
    it owes against chargebacks, so it can leave the platform under-reserved."""
    def decide(sim: CreatorMarketplace) -> float:
        return sim.owed
    return decide


def pay_monthly_policy(every: int = 4) -> Policy:
    """Batch: pay everything owed once every `every` periods, nothing in between.
    Safe for the platform, but creators wait."""
    def decide(sim: CreatorMarketplace) -> float:
        return sim.owed if (sim.t % every == every - 1) else 0.0
    return decide


def _reserve_floor_forecast(sim: CreatorMarketplace, horizon: int) -> list[float]:
    """Reserve required over the horizon: reserve_rate times the GMV expected to be
    exposed to chargebacks. Near-term uses the real current exposure; later periods
    use the steady-state window of forecast GMV."""
    p = sim.p
    steady = p.reserve_rate * p.chargeback_window * p.baseline_gmv
    out = [p.reserve_rate * sim.exposure()]
    out.extend(steady for _ in range(horizon))
    return out


def helm_payout_policy(controller: CashPayoutController) -> Policy:
    def decide(sim: CreatorMarketplace) -> float:
        H = controller.p.horizon
        dec = controller.plan(
            owed0=sim.owed,
            cash0=sim.cash,
            forecast_gmv=sim.forecast_gmv(H),
            reserve_floor=_reserve_floor_forecast(sim, H),
            cash_floor=sim.p.cash_floor,
        )
        return dec.payout
    return decide


def run_marketplace(sim: CreatorMarketplace, decide: Policy) -> MarketplaceMetrics:
    while not sim.done():
        sim.step(decide(sim))
    return MarketplaceMetrics.from_history(sim)
