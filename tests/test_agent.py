"""The agent layer, tested without a network.

The tool dispatcher is exercised against the real deterministic objects, and the
model loop is driven by a scripted fake LLM so the tool-calling plumbing (and
the AUP guard reached through the agent) is verified deterministically.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import HelmAgent, LLMClient  # noqa: E402
from agent.tools import HelmTools  # noqa: E402
from arms.awardsmith import DiscountTier, SupplierQuote  # noqa: E402
from helm_core import ControllerParams, RecedingHorizonController  # noqa: E402
from paypal import Ledger, PayPalClient  # noqa: E402
from simulator import BusinessParams, BusinessSim  # noqa: E402


def _tools():
    sim = BusinessSim(BusinessParams(), seed=7, n_periods=6)
    controller = RecedingHorizonController(ControllerParams(horizon=6))
    suppliers = [
        SupplierQuote("Alpha", [DiscountTier(0, 9.0)], capacity=200),
        SupplierQuote("Beta", [DiscountTier(0, 8.5), DiscountTier(40, 8.0)], capacity=200),
        SupplierQuote("Gamma", [DiscountTier(50, 7.5)], capacity=120),
    ]
    return HelmTools(sim, controller, suppliers, Ledger(), PayPalClient(env={"DEMO_MODE": "1"}))


def test_observe_reports_state():
    t = _tools()
    obs = t.observe()
    assert obs["period"] == 0
    assert obs["inventory"] == 120.0
    assert len(obs["forecast_demand"]) == 6


def test_plan_then_source_then_execute_advances_period():
    t = _tools()
    plan = t.plan_replenishment()
    assert plan["status"] in ("Optimal", "Feasible")
    src = t.source_suppliers(plan["recommended_order_qty"] or 60)
    assert src["status"] in ("Optimal", "Feasible")
    before = t.sim.t
    exe = t.execute_purchase(60)
    assert t.sim.t == before + 1
    assert exe["proposed_qty"] == 60.0          # what the model asked for is recorded
    assert exe["ordered_qty"] >= 0.0            # what the controller authority ran

def test_source_beats_naive_single_supplier():
    t = _tools()
    src = t.source_suppliers(100)
    # cheapest split should not cost more than the naive single-supplier buy
    assert src["naive_cost"] is None or src["total_cost"] <= src["naive_cost"]


def test_pay_partners_enforces_aup_through_agent_path():
    t = _tools()
    ok = t.pay_partners("b1", "COMMISSION", [{"email": "a@ex.com", "amount": 20}])
    assert ok["status"] == "completed"
    # forbidden purpose is caught by the verifier before the payout tool runs
    bad = t.pay_partners("b2", "PAYROLL", [{"email": "w@ex.com", "amount": 20}])
    assert bad["status"] in ("blocked", "rejected")
    assert not any(m["ref_id"] == "b2" for m in t.ledger.movements())


def test_model_proposed_zero_is_overruled_by_controller():
    # the model is not the authority: proposing 0 does not force no order; the
    # controller's recommended quantity runs instead, and the override is logged
    t = _tools()
    exe = t.execute_purchase(0)
    assert exe["proposed_qty"] == 0.0
    assert exe["ordered_qty"] > 0.0
    assert exe["verifier_overrides"]


class _FakeLLM(LLMClient):
    """Scripts a fixed sequence of tool-calls then a final narration."""

    def __init__(self, script):
        super().__init__(env={"HELM_LLM_API_KEY": "fake"})
        self._script = list(script)

    def chat(self, messages, tools=None, tool_choice="auto", temperature=0.0, max_tokens=700):
        return self._script.pop(0)


def _tool_msg(name, args):
    return {"role": "assistant", "content": "",
            "tool_calls": [{"id": f"c_{name}", "type": "function",
                            "function": {"name": name, "arguments": json.dumps(args)}}]}


def test_llm_loop_runs_tools_and_finishes():
    t = _tools()
    script = [
        _tool_msg("observe", {}),
        _tool_msg("plan_replenishment", {}),
        _tool_msg("execute_purchase", {"order_qty": 60}),
        _tool_msg("pay_partners", {"sender_batch_id": "x1", "purpose": "COMMISSION",
                                   "recipients": [{"email": "a@ex.com", "amount": 30}]}),
        {"role": "assistant", "content": "Ordered and paid the commission.", "tool_calls": None},
    ]
    agent = HelmAgent(t, _FakeLLM(script))
    run = agent.run("restock and pay the affiliate commission")
    names = [tc.name for tc in run.tool_calls]
    assert names == ["observe", "plan_replenishment", "execute_purchase", "pay_partners"]
    assert run.driver == "llm"
    assert "commission" in run.narration.lower()
    # the payout really went through the ledger
    assert any(m["ref_id"] == "x1" for m in t.ledger.movements())


def test_fallback_runs_without_key():
    t = _tools()
    agent = HelmAgent(t, LLMClient(env={}))  # no key
    run = agent.run("restock and pay partner commissions")
    assert run.driver == "fallback"
    assert any(tc.name == "execute_purchase" for tc in run.tool_calls)
    assert any(tc.name == "pay_partners" for tc in run.tool_calls)
    assert "Period" in run.narration
