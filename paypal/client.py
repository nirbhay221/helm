"""PayPal REST client with a keyless demo mode.

If PAYPAL_CLIENT_ID/SECRET are present and DEMO_MODE != 1, it does real
sandbox calls (OAuth client-credentials token, then JSON POSTs with a
PayPal-Request-Id idempotency header). Otherwise it runs in demo mode and
returns clearly-labeled synthetic responses (`_demo: True`, status
"DEMO_OK") so the whole system runs end to end with no keys and nothing ever
pretends a demo response is a live one.
"""
from __future__ import annotations

import os
import uuid


class PayPalClient:
    def __init__(self, env: dict | None = None) -> None:
        env = env if env is not None else os.environ
        self.client_id = env.get("PAYPAL_CLIENT_ID", "") or ""
        self.secret = env.get("PAYPAL_SECRET", "") or ""
        self.paypal_env = env.get("PAYPAL_ENV", "sandbox") or "sandbox"
        demo_flag = (env.get("DEMO_MODE", "1") or "1") == "1"
        self.demo = demo_flag or not (self.client_id and self.secret)
        self._token: str | None = None

    @property
    def base_url(self) -> str:
        return (
            "https://api-m.sandbox.paypal.com"
            if self.paypal_env == "sandbox"
            else "https://api-m.paypal.com"
        )

    def new_request_id(self) -> str:
        return str(uuid.uuid4())

    def _access_token(self) -> str:  # pragma: no cover - exercised only live
        if self._token:
            return self._token
        import requests

        resp = requests.post(
            f"{self.base_url}/v1/oauth2/token",
            data={"grant_type": "client_credentials"},
            auth=(self.client_id, self.secret),
            headers={"Accept": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        return self._token

    def post(self, path: str, body: dict, request_id: str | None = None) -> dict:
        """POST to PayPal (live) or synthesize a labeled demo response."""
        request_id = request_id or self.new_request_id()
        if self.demo:
            return {
                "_demo": True,
                "id": f"DEMO-{request_id[:8].upper()}",
                "status": "DEMO_OK",
                "_request_id": request_id,
                "_path": path,
                "echo": body,
            }
        import requests

        resp = requests.post(
            f"{self.base_url}{path}",
            json=body,
            headers={
                "Authorization": f"Bearer {self._access_token()}",
                "PayPal-Request-Id": request_id,
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        # PayPal uses 200/201 for success; surface the JSON either way
        data = resp.json() if resp.content else {}
        data.setdefault("_status_code", resp.status_code)
        return data

    def get(self, path: str) -> dict:  # pragma: no cover - exercised only live
        if self.demo:
            return {"_demo": True, "status": "DEMO_OK", "_path": path}
        import requests

        resp = requests.get(
            f"{self.base_url}{path}",
            headers={"Authorization": f"Bearer {self._access_token()}"},
            timeout=30,
        )
        return resp.json() if resp.content else {}
