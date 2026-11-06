"""Agent-to-agent commerce: a buyer's agent buys from a seller, under a mandate.

PayPal's own push right now is agentic commerce. This is our version on the
marketplace: a buyer's agent strikes a deal with a seller's listing and settles on
PayPal Orders, but it is boxed by the buyer's owner the way the field's strongest
entries do it:

  - the MANDATE (per-item cap, total budget, allowed categories, approval
    threshold) comes only from the owner, never from the seller or the listing
    text, so a malicious listing cannot widen what the agent may spend;
  - a deterministic fit check rejects any deal that breaks the mandate, so the
    agent cannot talk its way past its own limits;
  - a deal above the approval threshold is HELD for the owner, and the agent
    cannot approve itself (the gate is not a field the agent controls).

Negotiation is a simple price-fit; the judgment of which listing to pursue is the
buyer agent's. Settlement is real PayPal Orders (sandbox), idempotent per deal.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from paypal import Ledger, PayPalClient, capture_order, create_order

from .mandates import verify_credential
from .marketplace import Marketplace, Order


@dataclass
class Mandate:
    owner: str
    max_total: float
    max_per_item: float
    allowed_categories: tuple = ()        # empty means any category
    approval_threshold: float = 1e9       # a deal above this needs the owner's signed cart mandate
    nonce: str = ""                       # ties a cart mandate back to this intent

    def allows(self, category: str) -> bool:
        return (not self.allowed_categories) or category in self.allowed_categories

    @classmethod
    def from_payload(cls, p: dict) -> "Mandate":
        return cls(owner=p.get("owner", ""), max_total=float(p.get("max_total", 0)),
                   max_per_item=float(p.get("max_per_item", 0)),
                   allowed_categories=tuple(p.get("allowed_categories", []) or ()),
                   approval_threshold=float(p.get("approval_threshold", 1e9)),
                   nonce=p.get("nonce", ""))


@dataclass
class Deal:
    buyer: str
    seller: str
    listing: str
    category: str
    ask: float
    agreed: float
    status: str                            # settled | needs_owner_approval | blocked | no_deal
    reason: str
    order_id: str = None


@dataclass
class A2ADesk:
    market: Marketplace
    client: PayPalClient
    ledger: Ledger
    spent: float = 0.0                     # running total spent under the mandate
    _n: int = field(default=0)

    def negotiate(self, mandate: Mandate, listing) -> tuple:
        ask = listing.price
        if ask <= mandate.max_per_item:
            return round(ask, 2), "accepted at ask"
        offer = mandate.max_per_item
        if offer >= 0.8 * ask:             # seller's floor is 80% of ask
            return round(offer, 2), f"countered to {offer:.2f} (from {ask:.2f})"
        return None, f"ask {ask:.2f} exceeds per-item cap {mandate.max_per_item:.2f} and the seller floor"

    def fit(self, mandate: Mandate, category: str, price: float) -> tuple:
        if not mandate.allows(category):
            return False, "category", f"category '{category}' is not in the mandate"
        if price > mandate.max_per_item + 1e-6:
            return False, "per-item", f"{price:.2f} over the per-item cap {mandate.max_per_item:.2f}"
        if self.spent + price > mandate.max_total + 1e-6:
            return False, "total", f"{price:.2f} would breach the total budget {mandate.max_total:.2f}"
        return True, "ok", ""

    def _valid_cart(self, cart_credential, nonce: str, listing_id: str, agreed: float,
                    intent_pubkey: str) -> bool:
        """An over-threshold deal is only approved by a cart mandate the OWNER signed
        for this exact intent, listing and at least this amount. It must be signed by
        the SAME key as the intent, so an impostor's own-signed cart does not count,
        and the agent cannot self-approve."""
        if not cart_credential or cart_credential.get("public_key") != intent_pubkey:
            return False
        ok, p, _ = verify_credential(cart_credential)
        return bool(ok and p.get("type") == "CartMandate" and p.get("intent_nonce") == nonce
                    and p.get("listing") == listing_id and float(p.get("amount", 0)) + 1e-6 >= agreed)

    def buy(self, intent_credential: dict, listing_id: str, cart_credential: dict = None,
            buyer: str = "buyer-agent") -> Deal:
        ok, payload, reason = verify_credential(intent_credential)
        if not ok or payload.get("type") != "IntentMandate":
            return Deal(buyer, "", listing_id, "", 0.0, 0.0, "rejected_unverified",
                        f"intent mandate did not verify: {reason}")
        mandate = Mandate.from_payload(payload)
        listing = self.market.listings.get(listing_id)
        if listing is None:
            return Deal(buyer, "", listing_id, "", 0.0, 0.0, "no_deal", "no such listing")
        cat = listing.category
        agreed, note = self.negotiate(mandate, listing)
        base = dict(buyer=mandate.owner, seller=listing.seller, listing=listing_id, category=cat, ask=listing.price)
        if agreed is None:
            return Deal(**base, agreed=0.0, status="no_deal", reason=note)
        ok_fit, cap, why = self.fit(mandate, cat, agreed)
        if not ok_fit:
            return Deal(**base, agreed=agreed, status="blocked", reason=f"{cap}: {why}")
        if agreed > mandate.approval_threshold and not self._valid_cart(
                cart_credential, mandate.nonce, listing_id, agreed, intent_credential.get("public_key")):
            return Deal(**base, agreed=agreed, status="needs_owner_approval",
                        reason=f"{agreed:.2f} is over the threshold {mandate.approval_threshold:.2f}; "
                               "needs a cart mandate the owner signed for this exact deal")
        # settle on PayPal Orders (money in), idempotent per deal
        ref = f"a2a-{listing_id}-{self._n}"
        self._n += 1
        res = create_order(self.client, self.ledger, agreed, reference=ref, kind="order")
        capture_order(self.client, self.ledger, res.order_id, agreed)
        self.spent = round(self.spent + agreed, 2)
        self.market.place_order(Order(id=f"a2a{self._n:04d}", buyer=mandate.owner,
                                      seller=listing.seller, listing=listing_id,
                                      amount=agreed, day=0, status="fulfilled"))
        return Deal(**base, agreed=agreed, status="settled", reason=note, order_id=res.order_id)
