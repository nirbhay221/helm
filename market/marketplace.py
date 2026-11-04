"""A two-sided creator marketplace: personas, listings, orders, returns.

Each account is a persona that both sells (lists items) and buys (places orders).
An order is money in on PayPal (Orders); fulfilling it pays the seller (Payouts).
Returns and chargebacks happen on some orders, and they are what the abuse engine
reads to decide who is at fault.

The generated world plants the patterns the engine must catch: most people behave,
a few BUYERS are serial returners (they return across many different sellers), and
a few SELLERS ship bad goods (returns cluster on them across many buyers). Fault
follows whichever side the problem travels with.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Account:
    id: str
    name: str
    country: str
    status: str = "active"            # active | suspended
    joined_day: int = 0
    suspend_reason: str = ""


@dataclass
class Listing:
    id: str
    seller: str                      # account id
    title: str
    price: float
    category: str


@dataclass
class Order:
    id: str
    buyer: str                       # account id
    seller: str                      # account id
    listing: str
    amount: float
    day: int
    status: str = "paid"             # paid | fulfilled | returned | charged_back
    reason: str = ""


class Marketplace:
    def __init__(self) -> None:
        self.accounts: dict[str, Account] = {}
        self.listings: dict[str, Listing] = {}
        self.orders: list[Order] = []

    # --- core actions -------------------------------------------------------
    def add_account(self, acc: Account) -> Account:
        self.accounts[acc.id] = acc
        return acc

    def list_item(self, listing: Listing) -> Listing:
        self.listings[listing.id] = listing
        return listing

    def place_order(self, order: Order) -> Order:
        self.orders.append(order)
        return order

    def mark_return(self, order: Order, reason: str = "") -> None:
        order.status = "returned"
        order.reason = reason

    def mark_chargeback(self, order: Order, reason: str = "") -> None:
        order.status = "charged_back"
        order.reason = reason

    def suspend(self, account_id: str, reason: str) -> None:
        a = self.accounts.get(account_id)
        if a:
            a.status = "suspended"
            a.suspend_reason = reason

    # --- read / metrics -----------------------------------------------------
    def orders_as_buyer(self, acc_id: str) -> list[Order]:
        return [o for o in self.orders if o.buyer == acc_id]

    def orders_as_seller(self, acc_id: str) -> list[Order]:
        return [o for o in self.orders if o.seller == acc_id]

    @staticmethod
    def _bad(orders: list[Order]) -> list[Order]:
        return [o for o in orders if o.status in ("returned", "charged_back")]

    def buyer_stats(self, acc_id: str) -> dict:
        o = self.orders_as_buyer(acc_id)
        bad = self._bad(o)
        return {"orders": len(o), "bad": len(bad),
                "rate": round(len(bad) / len(o), 3) if o else 0.0,
                "distinct_counterparties": len({x.seller for x in bad})}

    def seller_stats(self, acc_id: str) -> dict:
        o = self.orders_as_seller(acc_id)
        bad = self._bad(o)
        return {"orders": len(o), "bad": len(bad),
                "rate": round(len(bad) / len(o), 3) if o else 0.0,
                "distinct_counterparties": len({x.buyer for x in bad})}


# --- a realistic world with planted abuse ----------------------------------
_FIRST = {"US": ["James", "Olivia", "Noah"], "IN": ["Aarav", "Diya", "Arjun"],
          "BR": ["Miguel", "Helena", "Davi"], "NG": ["Chidi", "Amara", "Emeka"],
          "GB": ["Oliver", "Amelia", "Harry"]}
_CATS = ["prints", "presets", "beats", "ebooks", "merch", "templates"]


def generate_marketplace(n_accounts: int = 120, seed: int = 7,
                         n_serial_returners: int = 3, n_bad_sellers: int = 3) -> Marketplace:
    import numpy as np
    rng = np.random.default_rng(seed)
    m = Marketplace()
    countries = list(_FIRST.keys())

    accs: list[Account] = []
    for i in range(n_accounts):
        c = str(rng.choice(countries))
        name = f"{rng.choice(_FIRST[c])} {chr(65 + int(rng.integers(0,26)))}."
        accs.append(m.add_account(Account(id=f"u{i:04d}", name=name, country=c,
                                          joined_day=int(rng.integers(0, 120)))))
    # everyone lists a couple of items
    lid = 0
    for a in accs:
        for _ in range(int(rng.integers(1, 4))):
            m.list_item(Listing(id=f"l{lid:05d}", seller=a.id,
                                title=f"{rng.choice(_CATS)} #{lid}", price=round(float(rng.uniform(5, 120)), 2),
                                category=str(rng.choice(_CATS))))
            lid += 1
    listings = list(m.listings.values())

    serial = set(a.id for a in accs[:n_serial_returners])
    bad_sellers = set(a.id for a in accs[n_serial_returners:n_serial_returners + n_bad_sellers])

    oid = 0
    for _ in range(n_accounts * 10):
        listing = listings[int(rng.integers(0, len(listings)))]
        buyer = accs[int(rng.integers(0, len(accs)))]
        if buyer.id == listing.seller:
            continue
        o = m.place_order(Order(id=f"o{oid:06d}", buyer=buyer.id, seller=listing.seller,
                                listing=listing.id, amount=listing.price,
                                day=int(rng.integers(0, 120)), status="fulfilled"))
        oid += 1
        # base return behaviour: rare
        p_return = 0.04
        if buyer.id in serial:
            p_return = 0.75                         # serial returner, across many sellers
        elif listing.seller in bad_sellers:
            p_return = 0.6                          # bad seller, across many buyers
        if rng.random() < p_return:
            if rng.random() < 0.3:
                m.mark_chargeback(o, "disputed charge")
            else:
                m.mark_return(o, "requested return")

    # inject clear, well-spread patterns so fault is unambiguous for the engine
    def _hit(o):
        (m.mark_chargeback if rng.random() < 0.3 else m.mark_return)(o, "abuse pattern")

    acc_ids = [a.id for a in accs]
    for sid in sorted(serial):                          # serial returner, many sellers
        for tgt in [x for x in rng.permutation(acc_ids).tolist() if x != sid][:16]:
            tl = [l for l in listings if l.seller == tgt]
            if not tl:
                continue
            lst = tl[int(rng.integers(0, len(tl)))]
            o = m.place_order(Order(id=f"o{oid:06d}", buyer=sid, seller=tgt, listing=lst.id,
                                    amount=lst.price, day=int(rng.integers(0, 120)), status="fulfilled"))
            oid += 1
            if rng.random() < 0.85:
                _hit(o)
    for sid in sorted(bad_sellers):                     # bad seller, many buyers
        sl = [l for l in listings if l.seller == sid]
        if not sl:
            continue
        for b in [x for x in rng.permutation(acc_ids).tolist() if x != sid][:16]:
            lst = sl[int(rng.integers(0, len(sl)))]
            o = m.place_order(Order(id=f"o{oid:06d}", buyer=b, seller=sid, listing=lst.id,
                                    amount=lst.price, day=int(rng.integers(0, 120)), status="fulfilled"))
            oid += 1
            if rng.random() < 0.80:
                _hit(o)
    return m
