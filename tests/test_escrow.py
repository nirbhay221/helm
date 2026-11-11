"""Pay-on-proof escrow holds funds, releases only when deterministic criteria pass,
voids otherwise, and refuses criteria an empty delivery could satisfy."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market.escrow import Criterion, Escrow  # noqa: E402
from paypal import Ledger, PayPalClient  # noqa: E402


def _ctx():
    return PayPalClient(env={}), Ledger(":memory:")      # keyless demo mode


def test_escrow_holds_then_releases_on_proof():
    c, l = _ctx()
    e = Escrow("ava", "ben", 200.0,
               [Criterion("delivered", "truthy"), Criterion("tests_passed", "at_least", 10)])
    assert e.fund(c, l)["status"] == "held"
    out = e.settle({"delivered": True, "tests_passed": 12}, c, l)
    assert out["status"] == "released"
    assert all(r["passed"] for r in out["criteria_results"])
    # exactly one capture booked on the authorization
    caps = [m for m in l.movements() if m["kind"] == "capture"]
    assert len(caps) == 1


def test_escrow_voids_when_proof_fails():
    c, l = _ctx()
    e = Escrow("ava", "ben", 200.0, [Criterion("tests_passed", "at_least", 10)])
    e.fund(c, l)
    out = e.settle({"tests_passed": 3}, c, l)
    assert out["status"] == "refunded"
    assert any(m["kind"] == "void" for m in l.movements())


def test_escrow_refuses_hackable_criteria():
    # a criterion an empty delivery already satisfies must be rejected before funding
    c, l = _ctx()
    e = Escrow("ava", "ben", 200.0, [Criterion("missing_field", "equals", None)])
    out = e.fund(c, l)
    assert out["status"] == "rejected"
    assert "trivially satisfiable" in out["reason"]


def test_escrow_needs_criteria():
    c, l = _ctx()
    e = Escrow("ava", "ben", 100.0, [])
    assert e.fund(c, l)["status"] == "rejected"
