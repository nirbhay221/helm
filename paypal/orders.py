"""Orders v2: money in (customer payments) and money out for buying (paying a
supplier who accepts PayPal is an ordinary purchase).

The controller times cash with authorize-then-capture: authorize holds the funds,
capture takes them (possibly partially), void releases an unused authorization,
refund returns captured money. Each move is idempotent (PayPal-Request-Id) and
recorded in the ledger only when PayPal actually accepted it: a refused call is
reported as failed with PayPal's own issue code, never as done. Demo mode returns
clearly-labeled synthetic responses so the loop runs with no keys.

Marketplace orders name the SELLING CREATOR as the payee (purchase_units.payee), so the
buyer's money goes to the creator and never pools in the platform's account. With
HELM_PAYPAL_MULTIPARTY=1 (an approved PayPal partner) the order also carries the
platform fee and DELAYED disbursement, and the platform later releases each seller's
funds with a referenced payout. A plain sandbox app refuses those two fields
(PLATFORM_FEES_NOT_SUPPORTED, DELAYED_DISBURSEMENT_NOT_SUPPORTED), so they are opt-in.

A server-side agent has no browser to approve a PayPal checkout. In the sandbox the
buyer's approval is stood in for by PayPal's documented test card as the order's
payment_source, which returns a real authorization or capture. Live, the buyer approves
in the PayPal button instead.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from .client import PayPalClient
from .ledger import Ledger

# PayPal's published sandbox test Visa (developer.paypal.com card testing); sandbox only.
_SANDBOX_CARD = {"card": {"number": "4032039317984658", "expiry": "2030-12", "security_code": "123",
                          "name": "Helm Sandbox Buyer",
                          "billing_address": {"address_line_1": "1 Main St", "admin_area_2": "San Jose",
                                              "admin_area_1": "CA", "postal_code": "95131",
                                              "country_code": "US"}}}


@dataclass
class OrderResult:
    status: str                        # created | completed | authorized | captured | voided | refunded | failed
    order_id: str | None
    amount: float
    intent: str
    demo: bool
    raw: dict
    error: str = ""                    # PayPal's issue code when the call was refused

    @property
    def ok(self) -> bool:
        return self.status != "failed"


def _amount_block(value: float, currency: str) -> dict:
    return {"currency_code": currency, "value": f"{float(value):.2f}"}


def accepted(resp: dict) -> bool:
    """True when PayPal accepted the call (or it is a labeled demo response)."""
    if resp.get("_demo"):
        return True
    return int(resp.get("_status_code", 200)) in (200, 201, 202, 204)


def issue_of(resp: dict) -> str:
    details = resp.get("details") or []
    if details:
        return str(details[0].get("issue") or resp.get("name") or "REFUSED")
    return str(resp.get("name") or resp.get("message") or "REFUSED")


def multiparty_enabled(env=None) -> bool:
    env = env if env is not None else os.environ
    return (env.get("HELM_PAYPAL_MULTIPARTY", "0") or "0") == "1"


def sandbox_buyer_source(client: PayPalClient):
    """The sandbox stand-in for a buyer's approval, or None in demo or live mode."""
    if client.demo or client.paypal_env != "sandbox":
        return None
    if (os.environ.get("HELM_SANDBOX_BUYER_CARD", "1") or "1") != "1":
        return None
    return _SANDBOX_CARD


def create_order(
    client: PayPalClient,
    ledger: Ledger,
    amount: float,
    currency: str = "USD",
    intent: str = "CAPTURE",           # CAPTURE (take now) or AUTHORIZE (hold)
    reference: str = "",
    kind: str = "order",               # "order" (money in) or "supplier" (money out)
    payee_email: str | None = None,    # the selling creator: the money goes to them, not the platform
    platform_fee: float | None = None, # Multiparty only: the platform's cut, taken inside the order
    payment_source: dict | None = None,
) -> OrderResult:
    pu: dict = {"amount": _amount_block(amount, currency), "reference_id": reference or "helm"}
    if payee_email:
        pu["payee"] = {"email_address": payee_email}
        if multiparty_enabled():
            instr: dict = {"disbursement_mode": "DELAYED"}
            if platform_fee and platform_fee > 0:
                instr["platform_fees"] = [{"amount": _amount_block(platform_fee, currency)}]
            pu["payment_instruction"] = instr
    body: dict = {"intent": intent, "purchase_units": [pu]}
    if payment_source:
        body["payment_source"] = payment_source
    resp = client.post("/v2/checkout/orders", body, request_id=client.new_request_id())
    demo = bool(resp.get("_demo", client.demo))
    if not accepted(resp):
        return OrderResult("failed", None, round(float(amount), 2), intent, demo, resp, issue_of(resp))
    order_id = resp.get("id") or f"ORDER-{reference or 'helm'}"
    status = "completed" if str(resp.get("status")) == "COMPLETED" else "created"
    ledger.record_movement(kind, "order", order_id, round(float(amount), 2), status)
    return OrderResult(status=status, order_id=order_id, amount=round(float(amount), 2),
                       intent=intent, demo=demo, raw=resp)


def capture_order(client: PayPalClient, ledger: Ledger, order_id: str,
                  amount: float, currency: str = "USD") -> OrderResult:
    resp = client.post(f"/v2/checkout/orders/{order_id}/capture", {},
                       request_id=client.new_request_id())
    demo = bool(resp.get("_demo", client.demo))
    if not accepted(resp):
        return OrderResult("failed", order_id, round(float(amount), 2), "CAPTURE", demo, resp, issue_of(resp))
    ledger.record_movement("capture", "order", order_id, round(float(amount), 2), "captured")
    return OrderResult(status="captured", order_id=order_id, amount=round(float(amount), 2),
                       intent="CAPTURE", demo=demo, raw=resp)


def authorize_order(client: PayPalClient, ledger: Ledger, order_id: str,
                    amount: float, currency: str = "USD") -> OrderResult:
    resp = client.post(f"/v2/checkout/orders/{order_id}/authorize", {},
                       request_id=client.new_request_id())
    demo = bool(resp.get("_demo", client.demo))
    if not accepted(resp):
        return OrderResult("failed", order_id, round(float(amount), 2), "AUTHORIZE", demo, resp, issue_of(resp))
    return OrderResult(status="authorized", order_id=order_id, amount=round(float(amount), 2),
                       intent="AUTHORIZE", demo=demo, raw=resp)


def authorization_id_from(resp: dict) -> str | None:
    """Pull the authorization id out of an order or authorize response. Only a demo
    response falls back to its own id: live, no authorization means no hold."""
    try:
        return resp["purchase_units"][0]["payments"]["authorizations"][0]["id"]
    except Exception:
        return resp.get("id") if resp.get("_demo") else None


def capture_id_from(resp: dict) -> str | None:
    try:
        return resp["purchase_units"][0]["payments"]["captures"][0]["id"]
    except Exception:
        return resp.get("id") if resp.get("_demo") else None


def capture_authorization(client: PayPalClient, ledger: Ledger, authorization_id: str,
                          amount: float, currency: str = "USD", final: bool = True) -> OrderResult:
    """Take money from a held authorization (Payments v2). Partial captures are
    allowed; `final` closes the authorization. Idempotent and booked once."""
    body = {"amount": _amount_block(amount, currency), "final_capture": bool(final)}
    resp = client.post(f"/v2/payments/authorizations/{authorization_id}/capture", body,
                       request_id=client.new_request_id())
    demo = bool(resp.get("_demo", client.demo))
    if not accepted(resp):
        return OrderResult("failed", authorization_id, round(float(amount), 2), "AUTHORIZE", demo, resp,
                           issue_of(resp))
    cap_id = resp.get("id") or authorization_id
    ledger.record_movement("capture", "authorization", authorization_id, round(float(amount), 2), "captured")
    return OrderResult(status="captured", order_id=cap_id, amount=round(float(amount), 2),
                       intent="AUTHORIZE", demo=demo, raw=resp)


def void_authorization(client: PayPalClient, ledger: Ledger, authorization_id: str) -> OrderResult:
    """Release a held authorization without charging it (Payments v2). This is the
    'proof failed, give the money back' side of pay-on-proof escrow."""
    resp = client.post(f"/v2/payments/authorizations/{authorization_id}/void", {},
                       request_id=client.new_request_id())
    demo = bool(resp.get("_demo", client.demo))
    if not accepted(resp):
        return OrderResult("failed", authorization_id, 0.0, "AUTHORIZE", demo, resp, issue_of(resp))
    ledger.record_movement("void", "authorization", authorization_id, 0.0, "voided")
    return OrderResult(status="voided", order_id=authorization_id, amount=0.0,
                       intent="AUTHORIZE", demo=demo, raw=resp)


def refund_capture(client: PayPalClient, ledger: Ledger, capture_id: str,
                   amount: float, currency: str = "USD") -> OrderResult:
    body = {"amount": _amount_block(amount, currency)}
    resp = client.post(f"/v2/payments/captures/{capture_id}/refund", body,
                       request_id=client.new_request_id())
    demo = bool(resp.get("_demo", client.demo))
    if not accepted(resp):
        return OrderResult("failed", capture_id, round(float(amount), 2), "REFUND", demo, resp, issue_of(resp))
    ledger.record_movement("refund", "capture", capture_id, round(float(amount), 2), "refunded")
    return OrderResult(status="refunded", order_id=capture_id, amount=round(float(amount), 2),
                       intent="REFUND", demo=demo, raw=resp)


def referenced_payout(client: PayPalClient, ledger: Ledger, capture_id: str, amount: float) -> OrderResult:
    """Multiparty: release a seller's DELAYED funds from one capture (referenced payout).
    This is how the platform decides WHEN a creator gets the money a buyer already paid
    them, without the money ever sitting in the platform's own balance."""
    resp = client.post("/v1/payments/referenced-payouts-items",
                       {"reference_id": capture_id, "reference_type": "TRANSACTION_ID"},
                       request_id=client.new_request_id())
    demo = bool(resp.get("_demo", client.demo))
    if not accepted(resp):
        return OrderResult("failed", capture_id, round(float(amount), 2), "DISBURSE", demo, resp, issue_of(resp))
    ledger.record_movement("disburse", "capture", capture_id, round(float(amount), 2), "disbursed")
    return OrderResult(status="disbursed", order_id=capture_id, amount=round(float(amount), 2),
                       intent="DISBURSE", demo=demo, raw=resp)


def pay_supplier(client: PayPalClient, ledger: Ledger, amount: float,
                 reference: str, currency: str = "USD") -> OrderResult:
    """A supplier purchase is an ordinary Orders capture from the operator."""
    return create_order(client, ledger, amount=amount, currency=currency,
                        intent="CAPTURE", reference=reference, kind="supplier")
