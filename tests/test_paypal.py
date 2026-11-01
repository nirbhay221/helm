"""PayPal execution layer (demo mode): the Payouts MCP tool's AUP gate,
idempotency, human-approval gate, and webhook dedupe. These run keyless."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from paypal import Ledger, PayPalClient, create_payout, handle_webhook


def _client():
    return PayPalClient(env={"DEMO_MODE": "1"})


def test_client_demo_mode_is_labeled():
    c = _client()
    assert c.demo is True
    resp = c.post("/v1/payments/payouts", {"x": 1})
    assert resp["_demo"] is True and resp["status"] == "DEMO_OK"


def test_payout_completes_for_allowed_purpose():
    c, led = _client(), Ledger()
    res = create_payout(
        c, led,
        recipients=[{"email": "a@ex.com", "amount": 20}, {"email": "b@ex.com", "amount": 30}],
        sender_batch_id="batch-1", purpose="REWARD",
    )
    assert res.status == "completed"
    assert res.total_amount == 50.0 and res.recipients == 2
    assert any(m["ref_id"] == "batch-1" for m in led.movements())


def test_payout_is_idempotent_on_sender_batch_id():
    c, led = _client(), Ledger()
    args = dict(
        recipients=[{"email": "a@ex.com", "amount": 20}],
        sender_batch_id="batch-dup", purpose="COMMISSION",
    )
    first = create_payout(c, led, **args)
    second = create_payout(c, led, **args)
    assert first.status == "completed"
    assert second.status == "duplicate"
    # only one movement booked
    assert sum(1 for m in led.movements() if m["ref_id"] == "batch-dup") == 1


def test_payout_rejects_forbidden_purpose():
    c, led = _client(), Ledger()
    res = create_payout(
        c, led,
        recipients=[{"email": "a@ex.com", "amount": 500}],
        sender_batch_id="batch-pay", purpose="PAYROLL",
    )
    assert res.status == "rejected"
    assert led.movements() == []


def test_payout_human_gate_then_release():
    c, led = _client(), Ledger()
    big = dict(
        recipients=[{"email": "a@ex.com", "amount": 1500}],
        sender_batch_id="batch-big", purpose="INCENTIVE",
    )
    held = create_payout(c, led, **big)
    assert held.status == "needs_approval"
    assert led.movements() == []  # no money moved
    released = create_payout(c, led, approved=True, **big)
    assert released.status == "completed"
    assert any(m["ref_id"] == "batch-big" for m in led.movements())


def test_webhook_dedupe():
    led = Ledger()
    event = {"id": "WH-1", "event_type": "PAYMENT.PAYOUTSBATCH.SUCCESS",
             "resource": {"batch_header": {"payout_batch_id": "B1",
                                           "amount": {"value": "50.00"}}}}
    first = handle_webhook(led, event)
    second = handle_webhook(led, event)
    assert first["status"] == "processed"
    assert second["status"] == "duplicate"


def test_idempotency_store():
    led = Ledger()
    new1, _ = led.remember("k", {"v": 1})
    new2, resp = led.remember("k", {"v": 999})
    assert new1 is True and new2 is False
    assert resp == {"v": 1}  # original response returned, not overwritten
