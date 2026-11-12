"""The multi-agent operator graph runs end to end and the guardrails still bind.

These run with NO model key (LLMClient(env={})), so every node takes its deterministic
fallback and the test is hermetic: no network, same result every time. The point is to
prove the GRAPH wiring and the dispose guardrails, not the model's judgment -- the live
model is exercised by tests/test_ai_golden.py. Even on the fallback path the risk analyst
must hold the risky creator and pay the clean one, and the deterministic tools must clamp.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import LLMClient, OperatorCreator, OperatorTools, SignalDesk
from agent.operator_graph import OperatorGraph
from marketplace import CashPayoutController, CashPayoutParams, CreatorMarketplace, MarketplaceParams
from paypal import Ledger, PayPalClient


def _build(init_cash=3000.0):
    gmv = [1000, 1000, 1400, 2600]
    creators = [
        OperatorCreator("Ava", "ava@x.com", 3.0, context="long-tenured, steady sales, clean refund history"),
        OperatorCreator("Ben", "ben@x.com", 2.0, context="brand new this week, just went viral with a spike"),
        OperatorCreator("Cy", "cy@x.com", 1.0, context="mid-tier, a year on platform, occasional small refunds"),
    ]
    p = MarketplaceParams(baseline_gmv=1000.0, take_rate=0.12, refund_rate=0.05, chargeback_rate=0.12,
                          chargeback_lag=2, chargeback_window=4, reserve_rate=0.30, cash_floor=300.0,
                          init_cash=init_cash, demand_series=[float(x) for x in gmv])
    sim = CreatorMarketplace(p, seed=7, n_periods=len(gmv))
    ctrl = CashPayoutController(CashPayoutParams(horizon=8, take_rate=0.12, refund_rate=0.05, chargeback_rate=0.12))
    llm = LLMClient(env={})                                   # no key -> deterministic fallback path
    tools = OperatorTools(sim, ctrl, creators, SignalDesk(llm), PayPalClient(env={}), Ledger())
    for c in creators:                                        # settled balances (older than the window)
        tools.led.accrue(c.name, 500.0, -9)
    return OperatorGraph(tools, llm, max_debate_rounds=1), tools


def test_graph_has_the_multi_agent_nodes():
    g, _ = _build()
    nodes = set(g.app.get_graph().nodes)
    for n in ("signal_analyst", "risk_analyst", "bull", "bear", "manager", "compliance_gate", "dispose"):
        assert n in nodes, f"missing graph node {n}"


def test_runs_end_to_end_and_produces_each_stage():
    g, _ = _build()
    st = g.step("A quiet, ordinary week.")
    assert st["risk_views"] and all("verdict" in v for v in st["risk_views"])
    assert st["debate"] and {d["role"] for d in st["debate"]} == {"bull", "bear"}
    assert "risk_multiplier" in st and st["risk_multiplier"] >= 1.0
    assert "decision" in st and "status" in st["decision"]
    assert st["driver"] == "fallback"                         # no key -> fallback, honestly marked


def test_fraud_signal_holds_the_risky_creator():
    g, _ = _build()
    st = g.step("Risk alert: a fraud and chargeback wave is hitting brand-new viral accounts this week.")
    held = {v["creator"] for v in st["risk_views"] if v["verdict"] == "hold"}
    paid_names = {a["creator"] for a in st["proposal"]}
    assert "Ben" in held                                      # the brand-new viral account is held
    assert "Ben" not in paid_names                            # and never proposed for payment
    assert "Ava" in paid_names                                # the clean, settled creator is paid


def test_debate_multiplier_is_bounded_and_dispose_clamps():
    g, tools = _build(init_cash=800.0)                        # tight cash forces the safe-release clamp
    st = g.step("A fraud wave this week.")
    assert st["risk_multiplier"] >= 1.0
    dec = st["decision"]
    # the guardrail invariant: whatever the agents proposed, the controller keeps cash
    # above the floor after paying (it sizes the release against forecast inflows).
    assert dec["cash_after"] >= tools.sim.p.cash_floor - 1e-6
    assert dec.get("reserve_ok_after") is True


def test_more_rounds_make_a_longer_debate():
    g, _ = _build()
    g.max_debate_rounds = 2
    g.app = g._build()
    st = g.step("A fraud wave this week.")
    assert len([d for d in st["debate"] if d["role"] == "bull"]) == 2


def test_a_second_round_runs_only_while_bull_and_bear_disagree():
    g, _ = _build()
    g.max_debate_rounds = 3
    apart = {"debate_round": 1, "debate": [{"role": "bull", "round": 1, "pushes": 1.0},
                                           {"role": "bear", "round": 1, "pushes": 1.5}]}
    close = {"debate_round": 1, "debate": [{"role": "bull", "round": 1, "pushes": 1.1},
                                           {"role": "bear", "round": 1, "pushes": 1.2}]}
    capped = {**apart, "debate_round": 3}
    assert g._debate_router(apart) == "continue"
    assert g._debate_router(close) == "decide"
    assert g._debate_router(capped) == "decide"
