"""Orders v2: money in (customer payments) and money out for buying (paying a
supplier who accepts PayPal is an ordinary purchase).

The controller times cash with authorize-then-capture: authorize holds the funds,
capture takes them (possibly partially), void releases an unused authorization,
refund returns captured money. Each move is idempotent (PayPal-Request-Id) and
recorded in the ledger. Demo mode returns clearly-labeled synthetic responses so
the loop runs with no keys; with sandbox credentials the same calls hit Orders v2.
"""
from __future__ import annotations

from dataclasses import dataclass

from .client import PayPalClient
from .ledger import Ledger


@dataclass
class OrderResult:
    status: str                        # created | authorized | captured | voided | refunded
    order_id: str | None
    amount: float
    intent: str
    demo: bool
    raw: dict


def _amount_block(value: float, currency: str) -> dict:
    return {"currency_code": currency, "value": f"{float(value):.2f}"}


def create_order(
    client: PayPalClient,
    ledger: Ledger,
    amount: float,
    currency: str = "USD",
    intent: str = "CAPTURE",           # CAPTURE (take now) or AUTHORIZE (hold)
    reference: str = "",
    kind: str = "order",               # "order" (money in) or "supplier" (money out)
) -> OrderResult:
    body = {
        "intent": intent,
        "purchase_units": [{
            "amount": _amount_block(amount, currency),
            "reference_id": reference or "helm",
        }],
    }
    resp = client.post("/v2/checkout/orders", body, request_id=client.new_request_id())
    order_id = resp.get("id") or f"ORDER-{reference or 'helm'}"
    status = "created"
    ledger.record_movement(kind, "order", order_id, round(float(amount), 2), status)
    return OrderResult(status=status, order_id=order_id, amount=round(float(amount), 2),
                       intent=intent, demo=bool(resp.get("_demo", client.demo)), raw=resp)


def capture_order(client: PayPalClient, ledger: Ledger, order_id: str,
                  amount: float, currency: str = "USD") -> OrderResult:
    resp = client.post(f"/v2/checkout/orders/{order_id}/capture", {},
                       request_id=client.new_request_id())
    ledger.record_movement("capture", "order", order_id, round(float(amount), 2), "captured")
    return OrderResult(status="captured", order_id=order_id, amount=round(float(amount), 2),
                       intent="CAPTURE", demo=bool(resp.get("_demo", client.demo)), raw=resp)


def authorize_order(client: PayPalClient, ledger: Ledger, order_id: str,
                    amount: float, currency: str = "USD") -> OrderResult:
    resp = client.post(f"/v2/checkout/orders/{order_id}/authorize", {},
                       request_id=client.new_request_id())
    return OrderResult(status="authorized", order_id=order_id, amount=round(float(amount), 2),
                       intent="AUTHORIZE", demo=bool(resp.get("_demo", client.demo)), raw=resp)


def refund_capture(client: PayPalClient, ledger: Ledger, capture_id: str,
                   amount: float, currency: str = "USD") -> OrderResult:
    body = {"amount": _amount_block(amount, currency)}
    resp = client.post(f"/v2/payments/captures/{capture_id}/refund", body,
                       request_id=client.new_request_id())
    ledger.record_movement("refund", "capture", capture_id, round(float(amount), 2), "refunded")
    return OrderResult(status="refunded", order_id=capture_id, amount=round(float(amount), 2),
                       intent="REFUND", demo=bool(resp.get("_demo", client.demo)), raw=resp)


def pay_supplier(client: PayPalClient, ledger: Ledger, amount: float,
                 reference: str, currency: str = "USD") -> OrderResult:
    """A supplier purchase is an ordinary Orders capture from the operator."""
    return create_order(client, ledger, amount=amount, currency=currency,
                        intent="CAPTURE", reference=reference, kind="supplier")
