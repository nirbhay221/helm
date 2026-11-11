"""One visitor's account: the shared state that makes Helm one product instead of separate demos.

Each session owns a live two-sided creator marketplace, and the visitor is one of its sellers.
Every capability reads and writes the same books:

  - the marketplace itself: 120 creators (with two planted fraud rings) plus you, their
    listings and their order history, so abuse and ring scans run on the market you trade in;
  - a per-creator ledger over those orders: each sale's net earnings (after the platform's
    take) is a dated lot the platform owes until it is paid, and returns and chargebacks claw
    it back. What the platform owes creators (its liabilities) and your own earnings are both
    computed from this ledger, never typed in;
  - the platform's safety fund, held as reserve lots;
  - the advance book (advances leave the fund, repayments return to it);
  - open pay-on-proof holds (a PayPal authorization waiting for delivery);
  - your owner key and the spend mandate it signed, with a running total spent under it;
  - a tamper-evident receipt chain of every money action, and the PayPal movement ledger.

So a sale credits the seller's ledger, a payout pays it down, a purchase from another creator
moves your earnings to theirs (the platform keeps its take), taking an advance shrinks the fund
and the solvency margin, and a suspended creator's earnings stay frozen until review. Lend too
much and the platform can no longer prove it is solvent.

Accounts live in memory, keyed by a per-browser session id, and are bounded (oldest evicted).
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Optional

from .advance import AdvanceEngine, SafetyFund
from .creator_ledger import CreatorLedger
from .receipts import ReceiptChain

ME = "me"                       # the visitor's own seller account id
NOW_DAY = 120                   # "today" in the marketplace's day clock
WINDOW = 30                     # chargeback window: earnings younger than this are still at risk
TAKE_RATE = 0.10                # the platform's cut of every sale
FUND_COVER = 1.6                # the safety fund starts at this multiple of what is owed
MAX_ACCOUNTS = 300
DEFAULT_MANDATE = 500.0         # the spend budget your owner key signs until you re-sign it

_MY_LISTINGS = (("Golden-hour Lightroom presets", 24.0, "presets"),
                ("Lo-fi beat pack vol. 2", 39.0, "beats"),
                ("Studio print, signed A3", 55.0, "prints"))


_TITLES = {"prints": ["Risograph city print", "Botanical art print", "Film photo print"],
           "presets": ["Moody film presets", "Portrait skin-tone presets", "Travel color presets"],
           "beats": ["Trap beat pack", "Lo-fi sample kit", "Drill drum loops"],
           "ebooks": ["Freelance pricing ebook", "Home studio guide", "Short-form video playbook"],
           "merch": ["Embroidered cap", "Enamel pin set", "Heavyweight logo tee"],
           "templates": ["Notion creator OS", "Media kit template", "Canva thumbnail pack"]}


def _payee_map() -> dict:
    """Seller id -> PayPal seller email, from HELM_SELLER_PAYEE_EMAILS (a JSON object).
    A seller without an entry is paid through the platform account."""
    try:
        m = json.loads(os.environ.get("HELM_SELLER_PAYEE_EMAILS", "") or "{}")
        return {str(k): str(v) for k, v in m.items() if v} if isinstance(m, dict) else {}
    except Exception:
        return {}


# full names for the creators the demo pays most often (top earners and the beat sellers the
# default searches reach), matching their PayPal sandbox seller accounts
_FULL_NAMES = {"u0036": "Davi Costa", "u0113": "Helena Brandt", "u0096": "Aarav Hegde",
               "u0025": "Amara Quaye", "u0030": "Helena Lindqvist", "u0084": "Aarav Desai",
               "u0105": "Helena Varga", "u0110": "Emeka Mensah", "u0112": "Diya Utkarsh"}


def _build_market():
    """The session's marketplace: the seeded world (rings planted) plus you as a seller with
    three listings and four months of your own sales."""
    import numpy as np

    from market.marketplace import Account as MAccount, Listing, Order, generate_marketplace
    m = generate_marketplace(seed=7)
    for l in m.listings.values():                         # readable titles that match the category
        names = _TITLES[l.category]
        l.title = names[int(l.id[1:]) % len(names)]
    for cid, full in _FULL_NAMES.items():                  # the creators with their own PayPal seller account
        if cid in m.accounts:
            m.accounts[cid].name = full
    m.add_account(MAccount(id=ME, name="You", country="US", joined_day=14, device_id="dev-you",
                           payment_fp="card-you", ip_prefix="ip-you", email_domain="helm.example"))
    for i, (title, price, cat) in enumerate(_MY_LISTINGS):
        m.list_item(Listing(id=f"lme{i}", seller=ME, title=title, price=price, category=cat))
    rng = np.random.default_rng(120)
    ring = {a.id for a in m.accounts.values() if a.device_id.startswith("dev-ring")}
    buyers = [a for a in m.accounts if a not in ring and a != ME]
    for k in range(130):
        lst = m.listings[f"lme{int(rng.integers(0, len(_MY_LISTINGS)))}"]
        day = int(rng.integers(14, NOW_DAY))
        o = m.place_order(Order(id=f"ome{k:04d}", buyer=buyers[int(rng.integers(0, len(buyers)))],
                                seller=ME, listing=lst.id, amount=lst.price, day=day, status="fulfilled"))
        if rng.random() < 0.04:
            m.mark_return(o, "requested return")
    return m


def _build_ledger(m) -> CreatorLedger:
    """Accrue every fulfilled sale's net earnings on its day; earnings older than the window
    were paid out in earlier cycles. The last two windows are still owed: the older one has
cleared its chargeback window (settled, safe to pay), the newest is still at risk."""
    led = CreatorLedger(chargeback_window=WINDOW)
    for o in sorted(m.orders, key=lambda x: x.day):
        if o.status == "fulfilled":
            led.accrue(o.seller, round(o.amount * (1 - TAKE_RATE), 2), o.day)
    cutoff = NOW_DAY - 2 * WINDOW
    for s in {o.seller for o in m.orders}:
        old = sum(l.amount for l in led._st(s).unpaid_lots if l.period < cutoff)
        if old > 0:
            led.pay(s, old, cutoff)
    return led


@dataclass
class Account:
    market: object = None                                # market.marketplace.Marketplace
    cledger: CreatorLedger = None
    reserve_lots: list = field(default_factory=list)
    engine: AdvanceEngine = field(default_factory=AdvanceEngine)
    receipts: ReceiptChain = field(default_factory=ReceiptChain)
    escrows: dict = field(default_factory=dict)          # escrow id -> {escrow, title, merchant, price, ...}
    events: list = field(default_factory=list)
    ledger: object = None                                # paypal.Ledger, created lazily
    owner_key: object = None                             # market.mandates.OwnerKey, the visitor's own key
    mandate: dict = None                                 # the intent mandate that key signed
    mandate_spent: float = 0.0                           # spent (or held) under that mandate
    payees: dict = field(default_factory=_payee_map)
    capture_orders: dict = field(default_factory=dict)   # PayPal capture id -> marketplace order id
    disputes: dict = field(default_factory=dict)         # PayPal dispute id -> {order_id, stages}
    _oid: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def __post_init__(self) -> None:
        if self.market is None:
            self.market = _build_market()
        if self.cledger is None:
            self.cledger = _build_ledger(self.market)
        if not self.reserve_lots:
            cover = round(self.owed_to_creators * FUND_COVER, 2)
            self.reserve_lots = [round(cover * 0.75, 2), round(cover * 0.20, 2), round(cover * 0.05, 2)]
        if self.owner_key is None:
            from market.mandates import OwnerKey
            self.owner_key = OwnerKey()
        if self.mandate is None:
            self.sign_mandate(DEFAULT_MANDATE)

    # --- books ---------------------------------------------------------------------------
    def get_ledger(self):
        if self.ledger is None:
            from paypal import Ledger
            self.ledger = Ledger(":memory:")
        return self.ledger

    def sellers(self) -> list:
        return sorted({o.seller for o in self.market.orders})

    @property
    def owed_to_creators(self) -> float:
        return round(sum(self.cledger.total_unpaid(s) for s in self.sellers()), 2)

    def held_spend(self) -> float:
        return round(sum(v["price"] for v in self.escrows.values()), 2)

    @property
    def my_earnings(self) -> float:
        return round(self.cledger.total_unpaid(ME) - self.held_spend(), 2)

    def reserves(self) -> float:
        return round(sum(self.reserve_lots), 2)

    def liabilities(self) -> float:
        return self.owed_to_creators

    def frozen(self, seller: str) -> bool:
        a = self.market.accounts.get(seller)
        return bool(a and a.status != "active")

    def payee_for(self, seller: str):
        return self.payees.get(str(seller))

    def _draw(self, amount: float) -> None:
        """Take cash out of the fund, largest lot first."""
        left = round(float(amount), 2)
        for i in sorted(range(len(self.reserve_lots)), key=lambda j: -self.reserve_lots[j]):
            if left <= 0:
                break
            take = min(self.reserve_lots[i], left)
            self.reserve_lots[i] = round(self.reserve_lots[i] - take, 2)
            left = round(left - take, 2)
        self.reserve_lots = [x for x in self.reserve_lots if x > 0.004] or [0.0]

    def _deposit(self, amount: float) -> None:
        self.reserve_lots.append(round(float(amount), 2))

    def log(self, action: str, ref: str, amount: float, text: str, meta: Optional[dict] = None) -> None:
        self.receipts.append(action, ref, amount, meta or {})
        self.events.append({"t": round(time.time(), 1), "action": action, "amount": round(amount, 2),
                            "text": text})
        del self.events[:-30]

    # --- the marketplace -----------------------------------------------------------------
    def name_of(self, seller: str) -> str:
        a = self.market.accounts.get(seller)
        return a.name if a else str(seller)

    def search_listings(self, query: str = "", max_price: Optional[float] = None, limit: int = 6) -> list:
        """Active creators' listings matching the query, as product dicts the buyer can choose."""
        words = [w for w in str(query or "").lower().split() if len(w) > 2]
        out = []
        for l in self.market.listings.values():
            if l.seller == ME or self.frozen(l.seller):
                continue
            if max_price and l.price > max_price:
                continue
            text = f"{l.title} {l.category}".lower()
            hits = sum(1 for w in words if w in text or w.rstrip("s") in text)
            if words and not hits:
                continue
            out.append((hits, -self.market.seller_stats(l.seller)["rate"], l))
        out.sort(key=lambda t: (t[0], t[1]), reverse=True)
        return [{"id": l.id, "title": l.title, "brand": self.name_of(l.seller), "merchant": self.name_of(l.seller),
                 "seller": l.seller, "listing": l.id, "price": l.price, "currency": "USD", "url": "",
                 "image": "", "category": l.category, "source": "marketplace",
                 "payee": self.payee_for(l.seller) or "platform account"} for _, _, l in out[:limit]]

    def record_sale(self, buyer: str, listing_id: str, amount: float) -> dict:
        """A completed marketplace sale: the order lands in the market and the seller's net
        earnings become a fresh lot the platform owes (still inside the chargeback window)."""
        from market.marketplace import Order
        l = self.market.listings[listing_id]
        self._oid += 1
        o = self.market.place_order(Order(id=f"olive{self._oid:04d}", buyer=buyer, seller=l.seller,
                                          listing=l.id, amount=round(float(amount), 2), day=NOW_DAY,
                                          status="fulfilled"))
        net = round(o.amount * (1 - TAKE_RATE), 2)
        self.cledger.accrue(l.seller, net, NOW_DAY)
        return {"order_id": o.id, "seller": l.seller, "gross": o.amount, "seller_net": net,
                "platform_fee": round(o.amount - net, 2)}

    def chargeback(self, order_id: str, reason: str = "disputed charge") -> dict:
        """A buyer disputed a marketplace order: mark it charged back and claw the seller's net
        earnings back (from unpaid earnings first, else as a debt recouped from future sales)."""
        o = next((x for x in self.market.orders if x.id == order_id), None)
        if o is None:
            return {"status": "unknown", "reason": "no such order"}
        if o.status in ("returned", "charged_back"):
            return {"status": "already", "order_id": o.id, "reason": f"order already {o.status}"}
        self.market.mark_chargeback(o, reason)
        net = round(o.amount * (1 - TAKE_RATE), 2)
        debt = self.cledger.chargeback(o.seller, net, NOW_DAY)
        self.log("chargeback", o.id, net, f"chargeback on {o.id}: clawed ${net:,.2f} back from {self.name_of(o.seller)}"
                 + (f" (${debt:,.2f} already paid, now owed back)" if debt else ""))
        return {"status": "charged_back", "order_id": o.id, "seller": o.seller, "clawed": net,
                "recoup_due": self.cledger.recoup_due(o.seller)}

    def scan(self, apply: bool = True) -> dict:
        """Run the abuse and ring engines on THIS market; suspended creators' earnings freeze."""
        from market.abuse import AbuseEngine
        from market.linkage import LinkageEngine
        verdicts = AbuseEngine().scan(self.market)
        rings = LinkageEngine().infer(self.market)
        suspended = []
        if apply:
            for v in verdicts:
                if v.action == "suspend" and v.account_id != ME:
                    self.market.suspend(v.account_id, v.reason)
                    suspended.append(v.account_id)
            for r in rings:
                if r.action == "suspend_ring":
                    for x in r.members:
                        if x != ME and not self.frozen(x):
                            self.market.suspend(x, f"member of ring {r.id}: {r.reason}")
                            suspended.append(x)
        frozen = {s: self.cledger.total_unpaid(s) for s in self.sellers() if self.frozen(s)}
        if suspended:
            self.log("suspend", ",".join(sorted(set(suspended)))[:60], sum(frozen.values()),
                     f"suspended {len(set(suspended))} accounts; ${sum(frozen.values()):,.2f} of their earnings frozen")
        return {"verdicts": verdicts, "rings": rings, "suspended": sorted(set(suspended)),
                "frozen_earnings": round(sum(frozen.values()), 2), "frozen": frozen}

    # --- advances ----------------------------------------------------------------------
    def fund(self) -> SafetyFund:
        return SafetyFund(self.reserves())

    def take_advance(self, creator: str, amount: float, proven_earnings: float, history=None) -> dict:
        f = self.fund()
        r = self.engine.take(creator, amount, proven_earnings, f, approved=True, earnings_history=history)
        if r.get("status") == "advanced":
            self._draw(r["amount"])
            self.log("advance", creator, r["amount"],
                     f"advanced ${r['amount']:,.2f} to {creator} from the safety fund (fee ${r['fee']:,.2f})")
        return r

    def repay_from_payout(self, creator: str, payout: float) -> dict:
        f = self.fund()
        r = self.engine.repay_from_payout(creator, payout, f)
        if r["withheld"] > 0:
            self._deposit(r["withheld"])
            self.log("repayment", creator, r["withheld"],
                     f"withheld ${r['withheld']:,.2f} from {creator}'s payout to repay the advance")
        return r

    # --- payouts (from the operator) --------------------------------------------------------
    def record_payouts(self, paid: list) -> list:
        """Pay creators from the ledger: never more than they are owed, never a frozen creator.
        Returns what was actually booked."""
        booked = []
        for p in paid or []:
            want = round(float(p.get("amount", 0)), 2)
            who = str(p.get("creator"))
            if want <= 0 or self.frozen(who):
                continue
            amt = self.cledger.pay(who, want, NOW_DAY)
            if amt <= 0:
                continue
            self._draw(amt)
            self.log("payout", who, amt, f"paid {self.name_of(who)} ${amt:,.2f} via PayPal Payouts")
            if who in self.engine.loans:
                self.repay_from_payout(who, amt)
            booked.append({"creator": who, "amount": amt})
        return booked

    # --- your spend mandate ------------------------------------------------------------------
    def sign_mandate(self, max_total: float, max_per_item: Optional[float] = None, categories=None) -> dict:
        """Your owner key signs a fresh intent mandate; spending under it starts from zero."""
        from market.mandates import issue_intent_mandate
        self.mandate = issue_intent_mandate(self.owner_key, owner=ME, max_total=float(max_total),
                                            max_per_item=float(max_per_item or max_total),
                                            allowed_categories=list(categories or []))
        self.mandate_spent = round(self.held_spend(), 2)
        return self.mandate

    def mandate_for(self, budget: Optional[float]) -> dict:
        """The mandate a spend runs under. A different budget is the owner re-signing."""
        from market.mandates import verify_credential
        ok, pl, _ = verify_credential(self.mandate or {}, expected_public_key=self.owner_key.public_pem())
        if budget and (not ok or abs(float(pl.get("max_total", 0)) - float(budget)) > 1e-6):
            self.sign_mandate(float(budget))
        return self.mandate

    def mandate_view(self) -> dict:
        from market.mandates import verify_credential
        ok, pl, _ = verify_credential(self.mandate or {}, expected_public_key=self.owner_key.public_pem())
        total = float(pl.get("max_total", 0)) if ok else 0.0
        return {"max_total": total, "max_per_item": float(pl.get("max_per_item", 0)) if ok else 0.0,
                "spent": round(self.mandate_spent, 2), "remaining": round(max(0.0, total - self.mandate_spent), 2),
                "signed_by": "your owner key", "verified": bool(ok)}

    # --- spending own earnings through pay-on-proof ----------------------------------------
    def can_spend(self, price: float) -> tuple:
        if price > self.my_earnings + 1e-6:
            return False, (f"you have ${self.my_earnings:,.2f} of earnings available; "
                           f"${price:,.2f} is more than you have earned")
        return True, "ok"

    def hold_purchase(self, title: str, price: float, merchant: str, client, listing: Optional[str] = None) -> dict:
        """Hold the buyer's own earnings in a PayPal authorization until delivery is confirmed.
        A marketplace listing names its creator as the PayPal payee when they have a seller account."""
        from market.escrow import Criterion, Escrow
        seller = None
        if listing and listing in self.market.listings:
            seller = self.market.listings[listing].seller
            if self.frozen(seller):
                return {"status": "rejected", "reason": f"{self.name_of(seller)} is suspended pending review"}
            merchant = self.name_of(seller)
        price = round(float(price), 2)
        e = Escrow(ME, merchant, price, [Criterion("delivered", "truthy")],
                   payee_email=self.payee_for(seller) if seller else None,
                   platform_fee=round(price * TAKE_RATE, 2) if seller else None)
        held = e.fund(client, self.get_ledger())
        if held["status"] != "held":
            return {"status": held["status"], "reason": held["reason"]}
        eid = uuid.uuid4().hex[:10]
        self.escrows[eid] = {"escrow": e, "title": title, "merchant": merchant, "price": e.amount,
                             "listing": listing if seller else None, "seller": seller}
        self.mandate_spent = round(self.mandate_spent + e.amount, 2)
        self.log("authorize", e.authorization_id or eid, e.amount,
                 f"held ${e.amount:,.2f} of your earnings for {title} ({merchant}) until delivery")
        return {"status": "held", "escrow_id": eid, "authorization_id": e.authorization_id,
                "amount": e.amount, "seller": seller, "payee": e.payee_email or "platform account",
                "reason": "held on PayPal until you confirm delivery"}

    def settle_purchase(self, eid: str, delivered: bool, client) -> dict:
        item = self.escrows.get(eid)
        if not item:
            return {"status": "unknown", "reason": "no open hold with that id"}
        e = item["escrow"]
        out = e.settle({"delivered": True} if delivered else {}, client, self.get_ledger())
        if out["status"] == "released":
            self.escrows.pop(eid, None)
            self.cledger.pay(ME, e.amount, NOW_DAY)              # your earnings paid the purchase
            if item.get("listing"):
                # a creator-to-creator sale: the money stays on the platform, the seller is owed
                # their net, and the platform keeps its take
                sale = self.record_sale(ME, item["listing"], e.amount)
                if e.capture_id:
                    self.capture_orders[e.capture_id] = sale["order_id"]
                out["sale"] = sale
                self.log("capture", e.authorization_id or eid, e.amount,
                         f"delivery confirmed: ${sale['seller_net']:,.2f} to {item['merchant']}'s earnings, "
                         f"${sale['platform_fee']:,.2f} platform fee",
                         {"order": sale["order_id"], "capture": e.capture_id, "delivered": True})
            else:
                self._draw(e.amount)                              # paid out to an outside merchant
                self.log("capture", e.authorization_id or eid, e.amount,
                         f"delivery confirmed: captured ${e.amount:,.2f} to {item['merchant']}")
        elif out["status"] == "refunded":
            self.escrows.pop(eid, None)
            self.mandate_spent = round(max(0.0, self.mandate_spent - e.amount), 2)
            self.log("void", e.authorization_id or eid, e.amount,
                     f"not delivered: voided the hold, ${e.amount:,.2f} back in your earnings")
        return {**out, "escrow_id": eid}

    # --- audit ---------------------------------------------------------------------------
    def reconcile(self) -> dict:
        """Our receipts (what we believe settled) against PayPal's movement record."""
        from .recon import reconcile
        expected = [{"ref": r["ref"], "amount": r["amount"]} for r in self.receipts.receipts
                    if r["action"] == "capture"]
        actual = [{"ref": m["ref_id"], "amount": m["amount"], "status": m.get("status")}
                  for m in (self.get_ledger().movements() if self.ledger else []) if m["kind"] == "capture"]
        return reconcile(expected, actual)

    def market_view(self) -> dict:
        sellers = self.sellers()
        frozen = [s for s in sellers if self.frozen(s)]
        recent = [o for o in self.market.orders if o.day >= NOW_DAY - WINDOW]
        return {"creators": len(sellers), "listings": len(self.market.listings),
                "orders": len(self.market.orders),
                "gmv_30d": round(sum(o.amount for o in recent if o.status == "fulfilled"), 2),
                "suspended": len(frozen),
                "frozen_earnings": round(sum(self.cledger.total_unpaid(s) for s in frozen), 2),
                "take_rate": TAKE_RATE, "day": NOW_DAY, "chargeback_window_days": WINDOW}

    def snapshot(self) -> dict:
        v = self.receipts.verify()
        margin = round(self.reserves() - self.liabilities(), 2)
        return {"reserves": self.reserves(), "liabilities": self.liabilities(), "margin": margin,
                "solvent": margin >= 0, "my_earnings": self.my_earnings,
                "my_settled": round(self.cledger.settled_unpaid(ME, NOW_DAY), 2),
                "market": self.market_view(), "mandate": self.mandate_view(),
                "advances_outstanding": self.engine.total_outstanding(),
                "advances": [{"creator": l.creator, "principal": l.principal, "outstanding": l.outstanding}
                             for l in self.engine.loans.values()],
                "open_holds": [{"escrow_id": k, "title": v2["title"], "merchant": v2["merchant"],
                                "amount": v2["price"], "payee": v2["escrow"].payee_email or "platform account"}
                               for k, v2 in self.escrows.items()],
                "receipts": len(self.receipts.receipts), "chain_intact": bool(v.get("intact")),
                "events": list(reversed(self.events[-8:]))}


class AccountStore:
    """Bounded, thread-safe map of session id -> Account (least recently used evicted)."""

    def __init__(self, cap: int = MAX_ACCOUNTS) -> None:
        self.cap = cap
        self._d: "OrderedDict[str, Account]" = OrderedDict()
        self._lock = threading.Lock()

    def get(self, sid: Optional[str]) -> Account:
        key = (sid or "public")[:64]
        with self._lock:
            acct = self._d.get(key)
            if acct is None:
                acct = Account()
                self._d[key] = acct
            self._d.move_to_end(key)
            while len(self._d) > self.cap:
                self._d.popitem(last=False)
            return acct

    def reset(self, sid: Optional[str]) -> Account:
        key = (sid or "public")[:64]
        with self._lock:
            self._d[key] = Account()
            return self._d[key]


STORE = AccountStore()
