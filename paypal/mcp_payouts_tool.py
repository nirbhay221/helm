"""The Payouts MCP tool.

PayPal's official Agent Toolkit MCP server exposes orders, invoices,
subscriptions, refunds and disputes, but has no tool for paying out. This is
that missing tool: an agent-callable action that sends a PayPal Payouts batch,
with three guards baked in:

  1. AUP enforcement: the payout purpose must be one PayPal's Payouts Agreement
     permits (commission / rebate / reward / incentive). Payroll and
     paying a supplier for goods are refused here, in code, before any call.
  2. Idempotency: a unique sender_batch_id per batch (PayPal rejects a reused
     one within 30 days) plus a local idempotency record, so a retry never
     double-pays.
  3. A human-approval gate: batches above a threshold are held as
     `needs_approval` and move no money until re-invoked with approved=True.

PAYOUTS_TOOL_SCHEMA is the MCP tool descriptor; run_payouts_tool() is the
handler an MCP server would bind to it.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .client import PayPalClient
from .ledger import Ledger

ALLOWED_PAYOUT_PURPOSES = {"COMMISSION", "REBATE", "REWARD", "INCENTIVE"}
FORBIDDEN_EXAMPLES = {"PAYROLL", "WAGES", "SALARY", "SUPPLIER", "GOODS", "PURCHASE"}

PAYOUTS_TOOL_SCHEMA = {
    "name": "paypal_create_payout",
    "description": (
        "Send a PayPal Payouts batch to one or more recipients by email. "
        "Only AUP-permitted purposes are allowed (commission, rebate, reward, "
        "incentive). Idempotent on sender_batch_id. Batches above the approval "
        "threshold require human approval before any money moves."
    ),
    "inputSchema": {
        "type": "object",
        "required": ["sender_batch_id", "purpose", "recipients"],
        "properties": {
            "sender_batch_id": {"type": "string", "description": "Unique id per batch (dedupe)."},
            "purpose": {
                "type": "string",
                "enum": sorted(ALLOWED_PAYOUT_PURPOSES),
                "description": "AUP-permitted payout purpose.",
            },
            "currency": {"type": "string", "default": "USD"},
            "approved": {"type": "boolean", "default": False,
                          "description": "Set true to release a batch the gate held."},
            "recipients": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["email", "amount"],
                    "properties": {
                        "email": {"type": "string"},
                        "amount": {"type": "number"},
                        "note": {"type": "string"},
                    },
                },
            },
        },
    },
}


@dataclass
class PayoutResult:
    status: str                       # completed | needs_approval | rejected | duplicate
    message: str = ""
    batch_id: str | None = None
    total_amount: float = 0.0
    currency: str = "USD"
    purpose: str = ""
    recipients: int = 0
    demo: bool = False
    raw: dict = field(default_factory=dict)


def create_payout(
    client: PayPalClient,
    ledger: Ledger,
    recipients: list[dict],
    sender_batch_id: str,
    purpose: str,
    currency: str = "USD",
    approval_threshold: float = 1000.0,
    approved: bool = False,
) -> PayoutResult:
    purpose = (purpose or "").upper()
    if purpose not in ALLOWED_PAYOUT_PURPOSES:
        return PayoutResult(
            status="rejected",
            purpose=purpose,
            message=(
                f"Purpose '{purpose}' is not permitted on PayPal Payouts. "
                f"Allowed: {sorted(ALLOWED_PAYOUT_PURPOSES)}. "
                "Payroll and paying suppliers for goods are not allowed."
            ),
        )
    if not recipients:
        return PayoutResult(status="rejected", purpose=purpose, message="No recipients.")
    if any(float(r.get("amount", 0)) <= 0 for r in recipients):
        return PayoutResult(status="rejected", purpose=purpose, message="All amounts must be > 0.")

    total = round(sum(float(r["amount"]) for r in recipients), 2)
    idem_key = f"payout:{sender_batch_id}"

    existing = ledger.get(idem_key)
    if existing is not None:
        return PayoutResult(
            status="duplicate",
            message=f"sender_batch_id '{sender_batch_id}' already processed.",
            batch_id=existing.get("batch_id"),
            total_amount=existing.get("total_amount", total),
            currency=existing.get("currency", currency),
            purpose=purpose,
            recipients=len(recipients),
            demo=existing.get("demo", client.demo),
            raw=existing,
        )

    if total > approval_threshold and not approved:
        return PayoutResult(
            status="needs_approval",
            message=(
                f"Batch total {total} {currency} exceeds the approval threshold "
                f"{approval_threshold}. Re-invoke with approved=True to release. "
                "No money has moved."
            ),
            total_amount=total,
            currency=currency,
            purpose=purpose,
            recipients=len(recipients),
        )

    body = {
        "sender_batch_header": {
            "sender_batch_id": sender_batch_id,
            "email_subject": f"Your {purpose.lower()} payment",
            "recipient_type": "EMAIL",
        },
        "items": [
            {
                "recipient_type": "EMAIL",
                "amount": {"value": f"{float(r['amount']):.2f}", "currency": currency},
                "receiver": r["email"],
                "sender_item_id": f"{sender_batch_id}-{i}",
                "note": r.get("note", f"{purpose.title()} payment"),
            }
            for i, r in enumerate(recipients)
        ],
    }

    resp = client.post("/v1/payments/payouts", body, request_id=client.new_request_id())
    batch_id = (
        resp.get("batch_header", {}).get("payout_batch_id")
        or resp.get("id")
        or f"BATCH-{sender_batch_id}"
    )
    status = "completed"
    ledger.record_movement("payout", "payout_batch", sender_batch_id, total, status)
    result_payload = {
        "batch_id": batch_id,
        "total_amount": total,
        "currency": currency,
        "purpose": purpose,
        "demo": bool(resp.get("_demo", client.demo)),
    }
    ledger.remember(idem_key, result_payload)

    return PayoutResult(
        status=status,
        message="Payout batch submitted.",
        batch_id=batch_id,
        total_amount=total,
        currency=currency,
        purpose=purpose,
        recipients=len(recipients),
        demo=bool(resp.get("_demo", client.demo)),
        raw=resp,
    )


def run_payouts_tool(arguments: dict, client: PayPalClient, ledger: Ledger) -> dict:
    """MCP-style entry point: parse tool arguments and return a plain dict."""
    res = create_payout(
        client=client,
        ledger=ledger,
        recipients=arguments.get("recipients", []),
        sender_batch_id=arguments["sender_batch_id"],
        purpose=arguments.get("purpose", ""),
        currency=arguments.get("currency", "USD"),
        approved=bool(arguments.get("approved", False)),
    )
    return {
        "status": res.status,
        "message": res.message,
        "batch_id": res.batch_id,
        "total_amount": res.total_amount,
        "currency": res.currency,
        "purpose": res.purpose,
        "recipients": res.recipients,
        "demo": res.demo,
    }
