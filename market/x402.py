"""x402-style agentic micropayments: pay-per-request, settled on PayPal.

x402 revives HTTP 402 Payment Required as a protocol for agents to pay for a resource
inline: the server answers an unpaid request with 402 and a requirements object (an
`accepts` array of payment options), the agent pays and retries with a signed payment,
and the server verifies and settles before serving the content. The reference
implementation settles in stablecoin; the protocol is rail-agnostic, so this settles the
micropayment on the PayPal sandbox instead, reusing Helm's signed intent token to bind
the payment to the exact resource and amount.

Grounded in the x402 open standard (x402.org): the 402 challenge, the `accepts`
requirements with scheme / maxAmountRequired / payTo, and verify-then-settle.
"""
from __future__ import annotations

from typing import Optional

from .guard import issue_intent_token, verify_intent_token

PAY_TO = "helm-sandbox-merchant"


def requirements(resource: str, amount: float, currency: str = "USD", ttl: int = 120) -> tuple:
    """Build the 402 payment requirements and a signed challenge bound to this request."""
    reqs = {
        "x402Version": 1,
        "error": "payment required",
        "accepts": [{
            "scheme": "exact",
            "network": "paypal-sandbox",
            "maxAmountRequired": round(float(amount), 2),
            "currency": currency,
            "resource": str(resource),
            "payTo": PAY_TO,
            "maxTimeoutSeconds": int(ttl),
        }],
    }
    challenge = issue_intent_token(str(resource), float(amount), "x402", ttl)
    return reqs, challenge


def settle(challenge: dict, resource: str, amount: float, client, ledger) -> dict:
    """Verify the agent's payment matches the challenge, then settle it on PayPal and
    unlock the resource. A wrong amount or an expired/reused challenge is refused."""
    ok, reason = verify_intent_token(challenge, str(resource), float(amount), "x402")
    if not ok:
        return {"granted": False, "status": 402, "reason": "payment rejected: " + reason}
    from market.escrow import Criterion, Escrow
    e = Escrow("agent", PAY_TO, float(amount), [Criterion("delivered", "truthy")])
    held = e.fund(client, ledger)
    settled = e.settle({"delivered": True}, client, ledger)
    if settled.get("status") != "released":
        return {"granted": False, "status": 402, "reason": "payment did not settle: " + str(settled.get("reason")),
                "held": held, "settled": settled}
    backend = "demo" if getattr(client, "demo", True) else "paypal-sandbox"
    return {"granted": True, "status": 200, "resource": str(resource),
            "payment_response": {"settled": settled.get("status"), "amount": round(float(amount), 2),
                                 "network": "paypal-sandbox", "payTo": PAY_TO},
            "held": held, "settled": settled, "backend": backend,
            "content": "unlocked: %s" % resource}
