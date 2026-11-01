"""PayPal execution layer in demo mode (no keys needed).

Shows the Payouts MCP tool: an AUP-permitted commission payout goes through; a
payroll payout is refused in code; a large batch is held for human approval,
then released; and a duplicated webhook is de-duplicated. With real sandbox
credentials in .env, the same calls hit PayPal and return real batch ids.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from paypal import (  # noqa: E402
    PAYOUTS_TOOL_SCHEMA,
    Ledger,
    PayPalClient,
    create_payout,
    handle_webhook,
)


def main() -> None:
    client = PayPalClient()  # demo unless PAYPAL creds + DEMO_MODE=0 in env
    ledger = Ledger()
    print(f"mode: {'DEMO (no keys)' if client.demo else 'LIVE sandbox'}")
    print(f"MCP tool exposed: {PAYOUTS_TOOL_SCHEMA['name']}\n")

    print("1) Commission payout to 3 partners (AUP-permitted):")
    r = create_payout(
        client, ledger,
        recipients=[
            {"email": "p1@ex.com", "amount": 42.50, "note": "Q4 commission"},
            {"email": "p2@ex.com", "amount": 18.00},
            {"email": "p3@ex.com", "amount": 25.25},
        ],
        sender_batch_id="demo-commissions-001", purpose="COMMISSION",
    )
    print(f"   -> {r.status}: batch={r.batch_id} total=${r.total_amount} demo={r.demo}\n")

    print("2) Payroll payout (forbidden by AUP, refused in code before any call):")
    r2 = create_payout(
        client, ledger,
        recipients=[{"email": "worker@ex.com", "amount": 3000}],
        sender_batch_id="demo-payroll-001", purpose="PAYROLL",
    )
    print(f"   -> {r2.status}: {r2.message}\n")

    print("3) Large reward batch (over threshold) is held for human approval:")
    big = dict(
        recipients=[{"email": "whale@ex.com", "amount": 1500}],
        sender_batch_id="demo-reward-big", purpose="REWARD",
    )
    held = create_payout(client, ledger, **big)
    print(f"   -> {held.status}: {held.message}")
    released = create_payout(client, ledger, approved=True, **big)
    print(f"   -> after approval: {released.status}: batch={released.batch_id}\n")

    print("4) Webhook delivered twice (deduped on event id):")
    event = {"id": "WH-DEMO-1", "event_type": "PAYMENT.PAYOUTSBATCH.SUCCESS",
             "resource": {"batch_header": {"payout_batch_id": "B-DEMO",
                                           "amount": {"value": "85.75"}}}}
    print(f"   -> {handle_webhook(ledger, event)['status']}")
    print(f"   -> {handle_webhook(ledger, event)['status']}\n")

    print("Ledger movements booked (idempotent):")
    for m in ledger.movements():
        print(f"   {m['kind']:>7} {m['ref_type']}:{m['ref_id']} ${m['amount']} [{m['status']}]")


if __name__ == "__main__":
    main()
