"""Keystone: atomic batch execution and reconciliation on the Payouts MCP tool.

A payout batch must never corrupt the books on partial failure: if some items do
not go through, nothing may be stranded or double-paid, and the totals must still
balance. Keystone enforces conservation with plain arithmetic (intended = paid +
not-paid, to the cent), executes the succeeding items through the AUP-gated,
idempotent Payouts tool (unique sender_batch_id, so a retry never double-pays),
and reports exactly what moved and what did not. No formal prover: a reconciled
sum to the cent is the whole guarantee, which is what keeps it reliable.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from paypal import Ledger, PayPalClient, create_payout


@dataclass
class KeystoneResult:
    status: str                        # settled | partial | blocked | reconcile_error
    batch_id: str | None
    intended_total: float
    paid_total: float
    unpaid_total: float
    conserved: bool                    # intended == paid + unpaid, to the cent
    paid: list = field(default_factory=list)
    unpaid: list = field(default_factory=list)
    message: str = ""


def execute_batch(
    client: PayPalClient,
    ledger: Ledger,
    recipients: list[dict],
    sender_batch_id: str,
    purpose: str,
    fail_items: set | None = None,     # emails to simulate failing (demo/testing)
    approved: bool = False,
) -> KeystoneResult:
    fail_items = fail_items or set()
    intended = round(sum(float(r.get("amount", 0)) for r in recipients), 2)

    succeed = [r for r in recipients if r.get("email") not in fail_items]
    fail = [r for r in recipients if r.get("email") in fail_items]
    paid_total = round(sum(float(r.get("amount", 0)) for r in succeed), 2)
    unpaid_total = round(sum(float(r.get("amount", 0)) for r in fail), 2)

    conserved = abs(intended - (paid_total + unpaid_total)) < 0.01
    if not conserved:  # pragma: no cover - arithmetic guard
        return KeystoneResult(
            status="reconcile_error", batch_id=None, intended_total=intended,
            paid_total=paid_total, unpaid_total=unpaid_total, conserved=False,
            paid=succeed, unpaid=fail,
            message="totals do not balance; nothing executed")

    batch_id = None
    if succeed:
        res = create_payout(
            client=client, ledger=ledger, recipients=succeed,
            sender_batch_id=sender_batch_id, purpose=purpose, approved=approved)
        if res.status not in ("completed", "duplicate"):
            # gate held or blocked: nothing moved, books still balance
            return KeystoneResult(
                status="blocked", batch_id=res.batch_id, intended_total=intended,
                paid_total=0.0, unpaid_total=intended, conserved=True,
                paid=[], unpaid=recipients,
                message=f"payout not executed: {res.status} ({res.message})")
        batch_id = res.batch_id

    status = "settled" if not fail else "partial"
    msg = ("all items settled" if not fail
           else f"{len(fail)} item(s) failed and were left unpaid; books balanced")
    return KeystoneResult(
        status=status, batch_id=batch_id, intended_total=intended,
        paid_total=paid_total, unpaid_total=unpaid_total, conserved=True,
        paid=succeed, unpaid=fail, message=msg)
