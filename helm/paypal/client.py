"""A small PayPal REST client for the calls Helm makes, with token caching and idempotency.

Every write carries an idempotency key: `PayPal-Request-Id` on Orders, and `sender_batch_id`
on Payouts (PayPal rejects a second batch with the same id, which the client turns into a
lookup of the first one). Credentials come from the environment, never from the repository.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Callable

BASES = {"sandbox": "https://api-m.sandbox.paypal.com", "live": "https://api-m.paypal.com"}

# transport(method, url, headers, body_bytes) -> (status, body_dict); swappable for tests.
Transport = Callable[[str, str, dict, bytes | None], tuple[int, dict]]


class PayPalError(Exception):
    def __init__(self, status: int, body: dict):
        self.status, self.body = status, body
        super().__init__(f"PayPal {status}: {body.get('name')} {body.get('message')}")


def urllib_transport(method: str, url: str, headers: dict, body: bytes | None) -> tuple[int, dict]:
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return r.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            return e.code, {"message": raw.decode(errors="replace")}


def short_id(key: str, prefix: str = "helm") -> str:
    """A stable, PayPal-safe id derived from a Helm idempotency key."""
    return f"{prefix}-{hashlib.sha256(key.encode()).hexdigest()[:24]}"


@dataclass
class PayPalClient:
    client_id: str
    client_secret: str
    env: str = "sandbox"
    transport: Transport = urllib_transport
    _token: str = ""
    _expires: float = 0.0
    calls: list[tuple[str, str, int]] = field(default_factory=list)

    @classmethod
    def from_env(cls, prefix: str = "PAYPAL") -> "PayPalClient":
        return cls(os.environ[f"{prefix}_CLIENT_ID"], os.environ[f"{prefix}_CLIENT_SECRET"],
                   os.environ.get("PAYPAL_ENV", "sandbox"))

    @property
    def base(self) -> str:
        return BASES[self.env]

    def token(self) -> str:
        if self._token and time.time() < self._expires - 60:
            return self._token
        basic = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        status, body = self.transport("POST", f"{self.base}/v1/oauth2/token",
                                      {"Authorization": f"Basic {basic}",
                                       "Content-Type": "application/x-www-form-urlencoded"},
                                      b"grant_type=client_credentials")
        if status != 200:
            raise PayPalError(status, body)
        self._token, self._expires = body["access_token"], time.time() + body.get("expires_in", 3000)
        return self._token

    def request(self, method: str, path: str, body: dict | None = None, request_id: str = "") -> tuple[int, dict]:
        headers = {"Authorization": f"Bearer {self.token()}", "Content-Type": "application/json"}
        if request_id:
            headers["PayPal-Request-Id"] = request_id
        status, out = self.transport(method, f"{self.base}{path}", headers,
                                     json.dumps(body).encode() if body is not None else None)
        self.calls.append((method, path, status))
        return status, out

    # ---- Payouts: commissions to affiliates ------------------------------------------------
    def payout_batch(self, batch_id: str, items: list[dict], subject: str = "Your commission") -> dict:
        status, out = self.request("POST", "/v1/payments/payouts", {
            "sender_batch_header": {"sender_batch_id": batch_id, "email_subject": subject},
            "items": items,
        })
        if status == 201:
            return out["batch_header"]
        if status == 400 and out.get("name") in ("USER_BUSINESS_ERROR", "DUPLICATE_REQUEST_ID"):
            return {"payout_batch_id": None, "batch_status": "DUPLICATE", "sender_batch_id": batch_id}
        raise PayPalError(status, out)

    def get_payout(self, payout_batch_id: str) -> dict:
        status, out = self.request("GET", f"/v1/payments/payouts/{payout_batch_id}")
        if status != 200:
            raise PayPalError(status, out)
        return out

    # ---- Orders: customer checkout and supplier purchases ------------------------------------
    def create_order(self, amount: str, request_id: str, reference: str, intent: str = "CAPTURE",
                     payee_email: str = "", vault_id: str = "") -> dict:
        unit: dict = {"reference_id": reference, "amount": {"currency_code": "USD", "value": amount}}
        if payee_email:
            unit["payee"] = {"email_address": payee_email}
        body: dict = {"intent": intent, "purchase_units": [unit]}
        if vault_id:  # merchant-initiated charge of a saved PayPal wallet; no buyer redirect needed
            body["payment_source"] = {"paypal": {"vault_id": vault_id}}
        status, out = self.request("POST", "/v2/checkout/orders", body, request_id=request_id)
        if status not in (200, 201):
            raise PayPalError(status, out)
        return out

    def capture(self, order_id: str, request_id: str) -> dict:
        status, out = self.request("POST", f"/v2/checkout/orders/{order_id}/capture", {}, request_id=request_id)
        if status not in (200, 201):
            raise PayPalError(status, out)
        return out

    def get_order(self, order_id: str) -> dict:
        status, out = self.request("GET", f"/v2/checkout/orders/{order_id}")
        if status != 200:
            raise PayPalError(status, out)
        return out

    # ---- Read-back: balances and transactions (needs Transaction search on the app) -----------
    def balances(self) -> dict:
        status, out = self.request("GET", "/v1/reporting/balances?currency_code=USD")
        if status != 200:
            raise PayPalError(status, out)
        return out

    # ---- Webhooks --------------------------------------------------------------------------------
    def verify_webhook(self, headers: dict, event: dict, webhook_id: str) -> bool:
        status, out = self.request("POST", "/v1/notifications/verify-webhook-signature", {
            "auth_algo": headers.get("paypal-auth-algo"),
            "cert_url": headers.get("paypal-cert-url"),
            "transmission_id": headers.get("paypal-transmission-id"),
            "transmission_sig": headers.get("paypal-transmission-sig"),
            "transmission_time": headers.get("paypal-transmission-time"),
            "webhook_id": webhook_id,
            "webhook_event": event,
        })
        return status == 200 and out.get("verification_status") == "SUCCESS"
