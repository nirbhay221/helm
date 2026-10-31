"""The PayPal executor: the same interface as the simulated one, but money really moves in sandbox.

* Commissions go out as one Payouts batch per week; its `sender_batch_id` is derived from the
  week's idempotency key, so a replayed week is refused by PayPal instead of paying twice.
* Supplier purchases are orders that charge Helm's saved PayPal wallet at the supplier
  storefront (merchant-initiated, `vault_id`), routed to each supplier's account as payee.
  Until the storefront app and the saved wallet are set up, a purchase is reported as not
  executed rather than faked, and the Auditor stops the week.
* Every move is mirrored into the ledger with its PayPal id, which is what the Auditor reads back.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from helm.model import Action
from helm.paypal.client import PayPalClient, PayPalError, short_id
from helm.sim.world import DailyWorld


@dataclass
class PayPalExecutor:
    world: DailyWorld
    helm: PayPalClient  # the business's own app: Payouts, customer orders, read-back
    affiliate_emails: dict[str, str]  # affiliate handle -> sandbox PayPal email
    supplier_emails: dict[str, str] = field(default_factory=dict)  # supplier id -> sandbox email
    storefront: PayPalClient | None = None  # the supplier storefront app that charges the saved wallet
    vault_id: str = ""  # Helm's saved PayPal wallet at the storefront

    def execute(self, monday: date, action: Action, key: str) -> list[dict]:
        if action.commission_rate is not None:
            self.world.set_commission(action.commission_rate)
        receipts: list[dict] = []

        for i, o in enumerate(action.orders):
            k = f"{key}:order:{i}:{o.supplier_id}"
            if not (self.storefront and self.vault_id and o.supplier_id in self.supplier_emails):
                receipts.append({"key": k, "kind": "order", "to": o.supplier_id, "qty": o.qty, "new": False,
                                 "error": "supplier storefront or saved wallet not set up"})
                continue
            amount = f"{o.cost:.2f}"
            try:
                order = self.storefront.create_order(amount, request_id=short_id(k), reference=f"{o.supplier_id}-{o.qty}",
                                                     payee_email=self.supplier_emails[o.supplier_id], vault_id=self.vault_id)
            except PayPalError as e:
                receipts.append({"key": k, "kind": "order", "to": o.supplier_id, "new": False, "error": str(e)})
                continue
            paid = order.get("status") == "COMPLETED"
            fresh = paid and self.world.place_order(monday, o, key=k, paypal_id=order["id"])
            receipts.append({"key": k, "kind": "order", "to": o.supplier_id, "qty": o.qty, "amount": amount,
                             "paypal_id": order["id"], "status": order.get("status"), "new": fresh})

        payable = [(i, p) for i, p in enumerate(action.payouts) if p.receiver in self.affiliate_emails]
        if payable:
            batch_id = short_id(f"{key}:payouts", prefix="helm-pay")
            items = [{
                "recipient_type": "EMAIL",
                "amount": {"value": f"{p.amount:.2f}", "currency": "USD"},
                "receiver": self.affiliate_emails[p.receiver],
                "note": f"Helm {p.purpose} for the week of {monday.isoformat()}",
                "sender_item_id": short_id(f"{key}:payout:{i}:{p.receiver}", prefix="item"),
            } for i, p in payable]
            try:
                header = self.helm.payout_batch(batch_id, items, subject="Your affiliate commission")
            except PayPalError as e:
                header = {"payout_batch_id": None, "batch_status": "ERROR", "error": str(e)}
            for i, p in payable:
                k = f"{key}:payout:{i}:{p.receiver}"
                ok = header.get("batch_status") in ("PENDING", "PROCESSING", "SUCCESS", "DUPLICATE")
                fresh = ok and self.world.pay(monday, p, key=k, paypal_id=header.get("payout_batch_id") or batch_id)
                receipts.append({"key": k, "kind": "payout", "to": p.receiver, "amount": p.amount,
                                 "paypal_id": header.get("payout_batch_id"), "status": header.get("batch_status"),
                                 "new": fresh, **({"error": header["error"]} if "error" in header else {})})
        return receipts
