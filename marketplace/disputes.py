"""Buyer disputes on marketplace sales: claw back from the seller, defend with the receipts.

When a buyer disputes a payment, PayPal sends CUSTOMER.DISPUTE.CREATED and holds the disputed
amount from the merchant of record. On a marketplace that merchant is the platform, so the
platform must recover it from the creator who made the sale, not eat it. This module:

  1. finds the marketplace order behind the dispute (the disputed transaction's
     seller_transaction_id is the capture id we booked at settlement; custom or
     invoice_number may carry our own order id);
  2. charges the order back in the seller's ledger: it eats their unpaid earnings first and
     becomes a recoup debt if already paid out (the CreatorLedger rule);
  3. re-runs the abuse and ring engines on the account's market, so a seller whose disputes
     now spread across many buyers is suspended and their earnings freeze;
  4. builds the seller's evidence from the tamper-evident receipt chain and the delivery
     confirmation, and submits it with provide-evidence only when PayPal says the dispute is
     WAITING_FOR_SELLER_RESPONSE (the only state that accepts merchant evidence);
  5. on CUSTOMER.DISPUTE.RESOLVED in the seller's favour, credits the clawed earnings back.

Grounded in PayPal's Customer Disputes API v1 (webhook resource fields dispute_id,
disputed_transactions[].seller_transaction_id, status, dispute_outcome.outcome_code; evidence as
multipart with an `input` JSON part of evidences[]) and the platform-liability model in which the
marketplace, as merchant of record, recovers losses from the connected seller.
"""
from __future__ import annotations

from .account import NOW_DAY, TAKE_RATE


def _order_for(acct, resource: dict):
    for tx in resource.get("disputed_transactions") or []:
        cap = tx.get("seller_transaction_id")
        if cap and cap in acct.capture_orders:
            return acct.capture_orders[cap]
        for key in ("custom", "invoice_number"):
            v = tx.get(key)
            if v and any(o.id == v for o in acct.market.orders):
                return v
    return None


def evidence_for(acct, order_id: str) -> dict:
    """The seller's evidence from the books: the order, the delivery confirmation, and the
    receipts that recorded it, anchored to the receipt chain's head hash."""
    o = next((x for x in acct.market.orders if x.id == order_id), None)
    caps = [c for c, oid in acct.capture_orders.items() if oid == order_id]
    recs = [r for r in acct.receipts.receipts if r["ref"] in caps or r["ref"] == order_id
            or order_id in str(r.get("meta", ""))]
    head = acct.receipts.receipts[-1]["hash"] if acct.receipts.receipts else ""
    lst = acct.market.listings.get(o.listing) if o else None
    notes = (f"Digital item '{lst.title if lst else o.listing if o else order_id}' sold on day {o.day if o else '?'} "
             f"for ${o.amount:,.2f}; the buyer confirmed delivery before funds were captured "
             f"(pay-on-proof escrow). {len(recs)} matching entries in a hash-chained receipt log, "
             f"chain head {head[:16]}.")
    return {"evidences": [{"evidence_type": "ITEM_DESCRIPTION",
                           "notes": notes[:2000]}],
            "receipts": recs, "chain_head": head, "capture_ids": caps}


def apply_dispute(acct, event: dict, client=None) -> dict:
    """Apply one dispute event to an account's books. Idempotent per dispute id and stage."""
    etype = str(event.get("event_type", ""))
    r = event.get("resource") or {}
    did = str(r.get("dispute_id") or event.get("id") or "")
    order_id = _order_for(acct, r)
    if not order_id:
        return {"status": "unmatched", "dispute_id": did,
                "reason": "no marketplace order matches the disputed transaction"}
    seen = acct.disputes.setdefault(did, {"order_id": order_id, "stages": []})
    if etype in seen["stages"]:
        return {"status": "duplicate", "dispute_id": did, "order_id": order_id}
    seen["stages"].append(etype)
    o = next(x for x in acct.market.orders if x.id == order_id)
    out: dict = {"status": "processed", "dispute_id": did, "order_id": order_id, "seller": o.seller,
                 "event_type": etype}
    if etype == "CUSTOMER.DISPUTE.CREATED":
        cb = acct.chargeback(order_id, f"PayPal dispute {did}: {r.get('reason', 'disputed')}")
        out["chargeback"] = cb
        scan = acct.scan(apply=True)
        out["seller_suspended"] = o.seller in scan["suspended"] or acct.frozen(o.seller)
        out["frozen_earnings"] = scan["frozen_earnings"]
        ev = evidence_for(acct, order_id)
        out["evidence"] = {k: ev[k] for k in ("evidences", "chain_head", "capture_ids")}
        out["evidence"]["receipts_cited"] = len(ev["receipts"])
        status = str(r.get("status", ""))
        if client is not None and not client.demo and status == "WAITING_FOR_SELLER_RESPONSE":
            resp = client.post_multipart(f"/v1/customer/disputes/{did}/provide-evidence",
                                         {"evidences": ev["evidences"]})
            from paypal.orders import accepted, issue_of
            out["evidence_submitted"] = accepted(resp)
            if not accepted(resp):
                out["evidence_error"] = issue_of(resp)
        else:
            out["evidence_submitted"] = False
            out["evidence_note"] = ("prepared; PayPal accepts merchant evidence only while the dispute is "
                                    "WAITING_FOR_SELLER_RESPONSE" + (" (current: %s)" % status if status else ""))
    elif etype == "CUSTOMER.DISPUTE.RESOLVED":
        code = str(((r.get("dispute_outcome") or {}).get("outcome_code")) or "")
        out["outcome"] = code
        if code == "RESOLVED_SELLER_FAVOUR" and o.status == "charged_back":
            net = round(o.amount * (1 - TAKE_RATE), 2)
            o.status = "fulfilled"
            acct.cledger.accrue(o.seller, net, NOW_DAY)
            acct.log("dispute_won", order_id, net, f"dispute {did} resolved for {acct.name_of(o.seller)}: "
                     f"${net:,.2f} credited back")
            out["credited_back"] = net
    return out


def simulated_dispute(acct, order_id: str, status: str = "WAITING_FOR_SELLER_RESPONSE",
                      reason: str = "MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED") -> dict:
    """A CUSTOMER.DISPUTE.CREATED event shaped like PayPal's, for an order in this account's
    market. Labeled simulated: it is applied to the books but never sent to PayPal."""
    caps = [c for c, oid in acct.capture_orders.items() if oid == order_id]
    o = next((x for x in acct.market.orders if x.id == order_id), None)
    acct._sim_n = getattr(acct, "_sim_n", 0) + 1
    return {"id": f"WH-SIM-{acct._sim_n:04d}", "event_type": "CUSTOMER.DISPUTE.CREATED",
            "resource": {"dispute_id": f"PP-D-SIM-{acct._sim_n:04d}", "reason": reason, "status": status,
                         "dispute_amount": {"currency_code": "USD", "value": f"{o.amount:.2f}" if o else "0.00"},
                         "disputed_transactions": [{"seller_transaction_id": caps[0] if caps else None,
                                                    "custom": order_id}]},
            "_simulated": True}
