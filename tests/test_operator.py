"""The money-out operator steers the loop; the tools size and hard-clamp it.

Keyless (no model key -> scripted fallback) and demo-mode PayPal, so it is
deterministic and never touches the network. The live model path is exercised by
scripts/demo_operator.py.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import LLMClient, MoneyOutOperator, OperatorCreator, OperatorTools, SignalDesk
from marketplace import CashPayoutController, CashPayoutParams, CreatorMarketplace, MarketplaceParams
from paypal import Ledger, PayPalClient

GMV = [1000, 1000, 1400, 2600, 1200, 900]
CREATORS = [
    OperatorCreator("Ava", "ava@ex.com", 3.0, context="long-tenured, steady, clean history"),
    OperatorCreator("Ben", "ben@ex.com", 2.0, context="brand new this week, just went viral"),
    OperatorCreator("Cy", "cy@ex.com", 1.0, context="mid-tier, a year on platform"),
]


def _build():
    params = MarketplaceParams(
        baseline_gmv=1000.0, take_rate=0.12, refund_rate=0.05, chargeback_rate=0.12,
        chargeback_lag=2, chargeback_window=4, reserve_rate=0.30, cash_floor=300.0,
        init_cash=900.0, demand_series=[float(x) for x in GMV])
    sim = CreatorMarketplace(params, seed=7, n_periods=len(GMV))
    controller = CashPayoutController(CashPayoutParams(
        horizon=8, take_rate=0.12, refund_rate=0.05, chargeback_rate=0.12))
    client = PayPalClient(env={"DEMO_MODE": "1"})
    desk = SignalDesk(LLMClient(env={}))      # no key -> fallback parser
    tools = OperatorTools(sim, controller, [OperatorCreator(**vars(c)) for c in CREATORS],
                          desk, client, Ledger())
    operator = MoneyOutOperator(tools, LLMClient(env={}))   # no key -> scripted operator
    return operator, tools


def test_operator_runs_the_cycles_and_pays_on_paypal():
    operator, _ = _build()
    records = operator.run(len(GMV))
    assert len(records) == len(GMV)
    assert all(r.driver == "fallback" for r in records)
    completed = [r for r in records if r.facts.get("status") == "completed"]
    assert completed and all(r.facts.get("batch_id") for r in completed)


def test_payout_never_exceeds_the_controllers_safe_release():
    operator, _ = _build()
    for r in operator.run(len(GMV)):
        cap = r.facts.get("safe_release_total")
        paid = r.facts.get("paid_total", 0.0)
        if cap is not None:
            assert paid <= cap + 1e-6               # the hard guardrail holds


def test_risky_creator_is_held_and_safe_ones_are_paid():
    operator, _ = _build()
    records = operator.run(len(GMV))
    paid_names = {p["creator"] for r in records for p in (r.facts.get("paid") or [])}
    assert "Ben" not in paid_names                  # brand-new viral creator held
    assert "Ava" in paid_names                      # long-tenured creator paid


def test_guardrail_clamps_an_overspend_and_drops_unknown_creators():
    operator, tools = _build()
    tools.led.accrue("Ava", 5000.0, period=0)   # a large real balance to overspend from
    tools.observe()
    cap = tools.size_safe_release(1.0)["safe_release_total"]
    # ask to pay far more than the safe cap, to a real and an unknown creator
    res = tools.pay_creators([{"creator": "Ava", "amount": 5000.0},
                              {"creator": "Ghost", "amount": 500}])
    assert res["paid_total"] <= cap + 1e-6                 # safe-release clamp holds
    assert any("Ghost" in o for o in res["guardrail_overrides"])
