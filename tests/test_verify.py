"""The formal verifier proves budget soundness as an unbounded invariant, shows the
guard set is necessary, and emits a signed verdict only for a mandate that verifies."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market.mandates import OwnerKey, issue_intent_mandate, verify_credential  # noqa: E402
from market.verify import (  # noqa: E402
    admits, necessity_counterexample, per_item_necessity, prove_budget_soundness,
    verify_mandate,
)


def test_budget_soundness_is_proven():
    r = prove_budget_soundness(500.0, 100.0)
    assert r["proven"] is True
    assert r["inductive_step"] == "unsat"          # no counterexample to the step exists


def test_guard_necessity_has_teeth():
    # dropping the running-total guard, Z3 finds admitted deals whose sum busts the budget
    r = necessity_counterexample(500.0, 100.0)
    assert r["busts"] is True
    assert r["total"] > 500.0
    assert all(p <= 100.0 + 1e-6 for p in r["prices"])   # each one still within the per-item cap


def test_per_item_guard_is_necessary():
    r = per_item_necessity(500.0, 100.0)
    assert r["needed"] is True
    assert 100.0 < r["example_price"] <= 500.0        # over the cap, still within budget
    # and when the cap is above the budget, it is redundant, not falsely flagged
    assert per_item_necessity(500.0, 600.0)["needed"] is False


def test_admits_enforces_every_clause():
    T, M, cats, thr = 500.0, 100.0, ("stocks",), 1e9
    assert admits(T, M, cats, thr, spent=0, price=100, category="stocks") is True
    assert admits(T, M, cats, thr, spent=0, price=101, category="stocks") is False     # per-item
    assert admits(T, M, cats, thr, spent=450, price=100, category="stocks") is False   # total
    assert admits(T, M, cats, thr, spent=0, price=50, category="bonds") is False        # category


def test_verify_mandate_signs_a_verdict_for_a_valid_mandate():
    cred = issue_intent_mandate(OwnerKey(), "ava", max_total=500, max_per_item=100,
                                allowed_categories=["stocks"])
    out = verify_mandate(cred)
    assert out["verified_signature"] is True
    assert out["result"] == "PROVEN_BOUNDED"
    # the verdict is itself a valid ES256 credential
    ok, payload, _ = verify_credential(out["verdict"])
    assert ok and payload["type"] == "AuthorizationVerdict"
    assert payload["budget_soundness"]["proven"] is True


def test_verify_mandate_rejects_a_tampered_mandate():
    cred = issue_intent_mandate(OwnerKey(), "dan", max_total=500, max_per_item=100,
                                allowed_categories=["stocks"])
    cred["payload"]["max_total"] = 1e9              # forge a bigger budget, do not re-sign
    out = verify_mandate(cred)
    assert out["verified_signature"] is False
    assert out["result"] == "REJECTED"
