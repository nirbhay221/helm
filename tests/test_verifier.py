"""The sound verifier bank: the LLM proposes, these dispose.

Verifies that the controller's quantity is authoritative over a model-proposed
one, that an order is clamped against a hard cash floor, and that payouts are
blocked when the purpose is not AUP-permitted, the amount is non-positive, or it
exceeds cash on hand.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.verifier import ActionVerifier  # noqa: E402
from arms.awardsmith import DiscountTier, SupplierQuote  # noqa: E402
from helm_core import ControllerParams, RecedingHorizonController  # noqa: E402
from simulator import BusinessParams, BusinessSim  # noqa: E402


def _suppliers():
    return [
        SupplierQuote("Alpha", [DiscountTier(0, 9.0)], capacity=400),
        SupplierQuote("Beta", [DiscountTier(0, 8.5), DiscountTier(40, 8.0)], capacity=400),
    ]


def _verifier(cash=2000.0, inv=120.0):
    params = BusinessParams(init_cash=cash, init_inventory=inv)
    sim = BusinessSim(params, seed=7, n_periods=6)
    controller = RecedingHorizonController(ControllerParams(horizon=6, max_order=200.0))
    return ActionVerifier(sim, controller, _suppliers())


def test_controller_quantity_overrules_model_proposal():
    v = _verifier()
    rec = v.controller_recommendation()
    # model proposes a wildly different number
    verdict = v.verify_order(rec + 500)
    assert abs(verdict.executed_value - rec) < 1.0   # authority wins (modulo clamps)
    assert verdict.repaired
    assert any("controller authority" in m for m in verdict.violations)


def test_order_proposal_matching_controller_is_not_flagged():
    v = _verifier()
    rec = v.controller_recommendation()
    verdict = v.verify_order(rec)
    assert not verdict.violations
    assert abs(verdict.executed_value - rec) < 1e-6


def test_order_clamped_by_hard_cash_floor():
    # almost no cash: even the controller's order cannot be afforded in full
    v = _verifier(cash=50.0, inv=10.0)
    verdict = v.verify_order(200)
    cheapest = 8.0
    assert verdict.executed_value <= 50.0 / cheapest + 1e-6
    assert any("cash below floor" in m for m in verdict.violations)


def test_payout_blocked_for_forbidden_purpose():
    v = _verifier()
    verdict = v.verify_payout([{"email": "w@ex.com", "amount": 100}], "PAYROLL")
    assert verdict.ok is False
    assert any("AUP" in m for m in verdict.violations)


def test_payout_blocked_when_over_cash():
    v = _verifier(cash=100.0)
    verdict = v.verify_payout([{"email": "a@ex.com", "amount": 500}], "COMMISSION")
    assert verdict.ok is False
    assert any("exceeds cash" in m for m in verdict.violations)


def test_payout_ok_when_affordable_and_permitted():
    v = _verifier(cash=1000.0)
    verdict = v.verify_payout([{"email": "a@ex.com", "amount": 50}], "COMMISSION")
    assert verdict.ok is True
    assert verdict.executed_value == 50.0
