"""The creator-marketplace treasury controller sits on a better payout frontier.

Deterministic (fixed GMV path, seeded). The win is not strict dominance, which
is impossible when the reserve you owe scales with sales, but a better point on
the frontier: Helm pays creators faster than monthly batching and stays far
better reserved than paying everyone immediately, without ever breaking the cash
floor.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marketplace import (CashPayoutController, CashPayoutParams, CreatorMarketplace,
                         MarketplaceParams, helm_payout_policy, pay_all_now_policy,
                         pay_monthly_policy, run_marketplace)

GMV = [1000]*5 + [1800, 2600, 3000, 2600, 1800] + [350, 300, 350, 450, 600] + [900]*9


def _params():
    return MarketplaceParams(
        baseline_gmv=1000.0, take_rate=0.12, refund_rate=0.05,
        chargeback_rate=0.12, chargeback_lag=2, chargeback_window=4,
        reserve_rate=0.30, cash_floor=300.0, init_cash=900.0,
        demand_series=[float(x) for x in GMV],
    )


def _fresh():
    return CreatorMarketplace(_params(), seed=7, n_periods=len(GMV))


def _runs():
    ctrl = CashPayoutController(CashPayoutParams(
        horizon=8, take_rate=0.12, refund_rate=0.05, chargeback_rate=0.12))
    return (
        run_marketplace(_fresh(), pay_all_now_policy()),
        run_marketplace(_fresh(), pay_monthly_policy(4)),
        run_marketplace(_fresh(), helm_payout_policy(ctrl)),
    )


def test_helm_pays_faster_than_monthly_batching():
    _, monthly, helm = _runs()
    assert helm.avg_wait < monthly.avg_wait


def test_helm_is_far_better_reserved_than_paying_everyone():
    pay_all, _, helm = _runs()
    assert helm.reserve_breaches < pay_all.reserve_breaches
    assert helm.reserve_shortfall < 0.6 * pay_all.reserve_shortfall


def test_helm_never_breaks_the_hard_cash_floor():
    _, _, helm = _runs()
    assert helm.cash_floor_breaches == 0


def test_sim_never_pays_more_than_creators_earned():
    # creators are owed (1 - take) of GMV; total paid can never exceed that
    pay_all, _, _ = _runs()
    earned = sum((1 - 0.12) * g for g in GMV)
    assert pay_all.total_paid <= earned + 1e-6
