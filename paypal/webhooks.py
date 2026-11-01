"""Idempotent PayPal webhook handling.

Every event is de-duplicated on its event id, so a retried or replayed delivery
is applied at most once. In live mode the signature should be verified first
(verify_signature hook); in demo mode that step is skipped and clearly noted.
"""
from __future__ import annotations

from .client import PayPalClient
from .ledger import Ledger


def verify_signature(client: PayPalClient, event: dict, headers: dict) -> bool:  # pragma: no cover
    """Live signature verification via /v1/notifications/verify-webhook-signature.
    Demo mode trusts the event (no network). Returns True when acceptable."""
    if client.demo:
        return True
    import os

    webhook_id = os.environ.get("PAYPAL_WEBHOOK_ID", "")
    if not webhook_id:
        return False
    body = {
        "transmission_id": headers.get("paypal-transmission-id"),
        "transmission_time": headers.get("paypal-transmission-time"),
        "cert_url": headers.get("paypal-cert-url"),
        "auth_algo": headers.get("paypal-auth-algo"),
        "transmission_sig": headers.get("paypal-transmission-sig"),
        "webhook_id": webhook_id,
        "webhook_event": event,
    }
    resp = client.post("/v1/notifications/verify-webhook-signature", body)
    return resp.get("verification_status") == "SUCCESS"


def handle_webhook(
    ledger: Ledger,
    event: dict,
    client: PayPalClient | None = None,
    headers: dict | None = None,
) -> dict:
    event_id = event.get("id")
    if not event_id:
        return {"status": "ignored", "reason": "missing event id"}

    event_type = event.get("event_type", "")

    if client is not None and not client.demo:
        if not verify_signature(client, event, headers or {}):
            return {"status": "rejected", "reason": "signature verification failed",
                    "event_id": event_id}

    is_new = ledger.record_event(event_id, event_type, event)
    if not is_new:
        return {"status": "duplicate", "event_id": event_id, "event_type": event_type}

    # Apply known events to the ledger (idempotent via movements UNIQUE).
    resource = event.get("resource", {}) or {}
    if event_type.startswith("PAYMENT.PAYOUTSBATCH"):
        batch_id = resource.get("batch_header", {}).get("payout_batch_id", event_id)
        amount = float(
            resource.get("batch_header", {}).get("amount", {}).get("value", 0) or 0
        )
        ledger.record_movement("payout", "payout_batch", batch_id, amount, event_type)
    elif event_type.startswith("CHECKOUT.ORDER") or event_type.startswith("PAYMENT.CAPTURE"):
        ref = resource.get("id", event_id)
        ledger.record_movement("order", "order", ref, 0.0, event_type)

    return {"status": "processed", "event_id": event_id, "event_type": event_type}
