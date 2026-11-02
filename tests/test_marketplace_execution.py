"""Live-payout execution turns controller decisions into guarded Payouts batches.

Demo mode (DEMO_MODE=1), so no live PayPal call; the live path is exercised by
scripts/demo_marketplace_live.py.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marketplace import (CashPayoutController, CashPayoutParams, Creator,
                         CreatorMarketplace, MarketplaceParams, run_marketplace_live)
from paypal import Ledger, PayPalClient

GMV = [1000, 1000, 1800, 2600, 3000, 900, 900]
CREATORS = [Creator("Ava", "ava@ex.com", 3.0), Creator("Ben", "ben@ex.com", 2.0),
            Creator("Cy", "cy@ex.com", 1.0)]


def _run():
    params = MarketplaceParams(
        baseline_gmv=1000.0, take_rate=0.12, refund_rate=0.05, chargeback_rate=0.12,
        chargeback_lag=2, chargeback_window=4, reserve_rate=0.30, cash_floor=300.0,
        init_cash=900.0, demand_series=[float(x) for x in GMV])
    sim = CreatorMarketplace(params, seed=7, n_periods=len(GMV))
    controller = CashPayoutController(CashPayoutParams(
        horizon=8, take_rate=0.12, refund_rate=0.05, chargeback_rate=0.12))
    client = PayPalClient(env={"DEMO_MODE": "1"})
    return run_marketplace_live(sim, controller, CREATORS, client, Ledger())


def test_execution_sends_guarded_payout_batches_to_real_creators():
    runs = _run()
    assert runs, "expected at least one payout batch"
    emails = {c.email for c in CREATORS}
    for r in runs:
        assert r.recipients, "a batch must have recipients"
        for rec in r.recipients:
            assert rec["email"] in emails
            assert rec["amount"] > 0


def test_small_batches_complete_and_large_ones_need_approval():
    runs = _run()
    completed = [r for r in runs if r.status == "completed"]
    held = [r for r in runs if r.status == "needs_approval"]
    # under-threshold batches go through (demo) with a batch id
    assert completed and all(r.batch_id for r in completed)
    assert all(r.demo for r in completed)
    # the spike makes at least one batch exceed the $1000 approval gate
    assert held and all(r.batch_id is None for r in held)
