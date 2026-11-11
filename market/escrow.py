"""Pay-on-proof escrow: hold the money, check the work, release by code only.

The strongest pattern in this hackathon is escrow where PayPal holds the funds and
a deterministic rule, never a model, decides release. We do that and harden the one
place it usually breaks: the acceptance check. The buyer's criteria are compiled
into deterministic predicates; an AI may DRAFT them, but a model never decides the
release. We also run the field's "second AI attacks it" idea as a guard: a cheat
attempt (empty or garbage delivery) must FAIL the criteria before any funds are
held, so a check that any junk passes is rejected up front. Then money moves:
authorize to hold, capture on proof, void on failure, each booked once in the
ledger.

Grounded in: deterministic guardrails for judge-driven pipelines (LLM-as-a-judge is
not an oracle), one-token reward-hacking of LLM judges (so release stays code), and
PayPal Orders/Payments authorize-capture-void. Reuses this repo's paypal module.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Criterion:
    key: str                      # a field the delivery must provide
    predicate: str = "truthy"     # truthy | equals | at_least
    expected: object = None

    def check(self, delivery: dict) -> bool:
        v = delivery.get(self.key)
        if self.predicate == "truthy":
            return bool(v)
        if self.predicate == "equals":
            return v == self.expected
        if self.predicate == "at_least":
            try:
                return float(v) >= float(self.expected)
            except Exception:
                return False
        return False


@dataclass
class Escrow:
    """One escrowed deal. Criteria are fixed at funding time; release is a pure
    function of the delivery against those criteria."""
    buyer: str
    seller: str
    amount: float
    criteria: list = field(default_factory=list)      # Criterion
    status: str = "draft"                              # draft|held|released|refunded|rejected
    authorization_id: str | None = None
    reason: str = ""
    payee_email: str | None = None     # the selling creator, when they have a PayPal seller account
    platform_fee: float | None = None  # the platform's cut (taken in-order only under Multiparty)
    capture_id: str | None = None

    def _empty_delivery_passes(self) -> bool:
        """The adversarial guard: an empty delivery must NOT satisfy the criteria,
        or the criteria are hackable and we refuse to hold funds against them."""
        return all(c.check({}) for c in self.criteria) if self.criteria else True

    def fund(self, client, ledger) -> dict:
        """Hold the money with a PayPal authorization, but only after the criteria
        survive the empty-delivery attack."""
        if not self.criteria:
            self.status, self.reason = "rejected", "no acceptance criteria to prove against"
            return self._state()
        if self._empty_delivery_passes():
            self.status, self.reason = "rejected", "criteria are trivially satisfiable (empty delivery passes); refusing to hold funds"
            return self._state()
        from paypal import authorization_id_from, authorize_order, create_order, sandbox_buyer_source
        src = sandbox_buyer_source(client)
        order = create_order(client, ledger, self.amount, intent="AUTHORIZE", reference="escrow",
                             payee_email=self.payee_email, platform_fee=self.platform_fee,
                             payment_source=src)
        if not order.ok:
            self.status, self.reason = "failed", f"PayPal refused the hold: {order.error}"
            return self._state()
        if order.status == "completed":                 # authorized in one step via the payment source
            self.authorization_id = authorization_id_from(order.raw)
        else:
            auth = authorize_order(client, ledger, order.order_id, self.amount)
            if not auth.ok:
                self.status, self.reason = "failed", f"PayPal refused the hold: {auth.error}"
                return self._state()
            self.authorization_id = authorization_id_from(auth.raw)
        if not self.authorization_id:
            self.status, self.reason = "failed", "PayPal returned no authorization, so nothing is held"
            return self._state()
        self.status, self.reason = "held", "funds authorized and held on PayPal pending proof"
        return self._state()

    def settle(self, delivery: dict, client, ledger) -> dict:
        """Release on proof, refund (void the hold) otherwise. Code decides, from the
        criteria fixed at funding; the delivery's own fields never move the gate."""
        if self.status != "held":
            self.reason = f"cannot settle from status '{self.status}'"
            return self._state()
        results = [{"key": c.key, "passed": c.check(delivery)} for c in self.criteria]
        passed = all(r["passed"] for r in results)
        from paypal import capture_authorization, void_authorization
        if passed:
            cap = capture_authorization(client, ledger, self.authorization_id, self.amount)
            if not cap.ok:
                self.reason = f"criteria met but PayPal refused the capture: {cap.error}; still held"
                return {**self._state(), "criteria_results": results}
            self.capture_id = cap.order_id
            self.status, self.reason = "released", "all criteria met; captured"
        else:
            v = void_authorization(client, ledger, self.authorization_id)
            if not v.ok:
                self.reason = f"criteria failed but PayPal refused the void: {v.error}; still held"
                return {**self._state(), "criteria_results": results}
            failed = [r["key"] for r in results if not r["passed"]]
            self.status, self.reason = "refunded", f"criteria not met ({', '.join(failed)}); authorization voided"
        return {**self._state(), "criteria_results": results}

    def _state(self) -> dict:
        return {"buyer": self.buyer, "seller": self.seller, "amount": round(self.amount, 2),
                "status": self.status, "authorization_id": self.authorization_id,
                "capture_id": self.capture_id, "payee": self.payee_email or "platform account",
                "reason": self.reason, "criteria": [c.key for c in self.criteria]}
