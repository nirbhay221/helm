"""What each role can look at in the control room, besides the live map.

A buyer browses a catalog (creators on Helm first, then real stores through Channel3) and either
buys an item themselves or hands it to their buyer agent. A creator sees their own shop: listings,
what each one sold, and recent sales. The operator sees every account ranked by risk, the review
queue, with the evidence for each score. Agents only help when discovery is good (Magentic
Marketplace, Microsoft Research 2025), so the people using Helm get the same view the agents get.
"""
from __future__ import annotations

from collections import Counter

CATS = ("presets", "beats", "prints", "ebooks", "merch", "templates")


def _words(q: str) -> list:
    import re
    from marketplace.account import _STOP
    return [w for w in re.findall(r"[a-z0-9]+", str(q or "").lower()) if len(w) > 2 and w not in _STOP]


def catalog(acct, q: str = "", category: str = "", max_price: float | None = None, limit: int = 48) -> list:
    """Creator listings on this marketplace, best match first, then the best sellers."""
    from marketplace.account import ME
    m = acct.market
    words = _words(q)
    sales = Counter(o.seller for o in m.orders)
    lsales = Counter(o.listing for o in m.orders if o.status == "fulfilled")
    rows = []
    for l in m.listings.values():
        if category and l.category != category:
            continue
        if max_price and l.price > max_price:
            continue
        import re
        toks = set(re.findall(r"[a-z0-9]+", f"{l.title} {l.category}".lower()))
        toks |= {t.rstrip("s") for t in toks}
        hits = sum(1 for w in words if w in toks or w.rstrip("s") in toks)
        if words and not hits:
            continue
        st = m.seller_stats(l.seller)
        rows.append((hits, lsales[l.id], {
            "id": l.id, "title": l.title, "price": l.price, "category": l.category, "seller": l.seller,
            "seller_name": "You" if l.seller == ME else acct.name_of(l.seller), "mine": l.seller == ME,
            "suspended": acct.frozen(l.seller), "sold": lsales[l.id], "seller_sales": sales[l.seller],
            "return_rate": st["rate"], "trust": st["trust"], "new": l.id.startswith(("me", "lag")),
            "paypal_payee": bool(acct.payee_for(l.seller))}))
    rows.sort(key=lambda t: (t[0], not t[2]["mine"], not t[2]["suspended"], t[2]["new"], t[1]), reverse=True)
    return [r for _, _, r in rows[:limit]]


def stores(acct, q: str, max_price: float | None = None, limit: int = 8) -> dict:
    """Real products from Channel3, remembered for this session so a direct buy uses the price
    Channel3 returned, not one sent back by the browser."""
    from market.shopping import Channel3Client
    if not _words(q):
        return {"backend": "none", "products": []}
    products, backend = Channel3Client().search(q, max_price=max_price, limit=limit)
    cache = acct.__dict__.setdefault("store_cache", {})
    out = []
    for p in products:
        pid = str(p.get("id") or p.get("title"))[:80]
        cache[pid] = p
        out.append({"id": pid, "title": p.get("title"), "price": p.get("price"), "brand": p.get("brand"),
                    "merchant": p.get("merchant"), "image": p.get("image"), "url": p.get("url")})
    return {"backend": backend, "products": out}


def my_shop(acct) -> dict:
    from marketplace.account import ME, NOW_DAY
    m = acct.market
    mine = [l for l in m.listings.values() if l.seller == ME]
    by = {}
    for o in m.orders:
        if o.seller == ME:
            b = by.setdefault(o.listing, {"sold": 0, "revenue": 0.0, "returns": 0})
            if o.status == "fulfilled":
                b["sold"] += 1
                b["revenue"] = round(b["revenue"] + o.amount, 2)
            else:
                b["returns"] += 1
    listings = [{"id": l.id, "title": l.title, "price": l.price, "category": l.category,
                 **by.get(l.id, {"sold": 0, "revenue": 0.0, "returns": 0})} for l in mine]
    listings.sort(key=lambda r: -r["revenue"])
    sales = [{"order": o.id, "listing": (m.listings.get(o.listing).title if m.listings.get(o.listing) else o.listing),
              "buyer": acct.name_of(o.buyer), "amount": o.amount, "status": o.status, "day": o.day}
             for o in m.orders if o.seller == ME][-25:][::-1]
    st = m.seller_stats(ME)
    return {"listings": listings, "sales": sales,
            "summary": {"listings": len(mine), "orders": st["orders"], "return_rate": st["rate"],
                        "owed_to_you": round(acct.cledger.total_unpaid(ME), 2),
                        "settled_now": round(acct.cledger.settled_unpaid(ME, NOW_DAY), 2),
                        "spendable": acct.my_earnings, "payee": acct.payee_for(ME) or ""},
            "delisted": [{"id": k, "title": v.title, "price": v.price}
                         for k, v in (acct.__dict__.get("delisted") or {}).items()]}


def accounts(acct) -> list:
    """Every account with the evidence an operator needs, riskiest first."""
    from marketplace.account import ME
    m = acct.market
    dev = Counter(a.device_id for a in m.accounts.values() if a.device_id)
    card = Counter(getattr(a, "payment_fp", "") for a in m.accounts.values() if getattr(a, "payment_fp", ""))
    ip = Counter(a.ip_prefix for a in m.accounts.values() if a.ip_prefix)
    rows = []
    for a in m.accounts.values():
        ss, bs = m.seller_stats(a.id), m.buyer_stats(a.id)
        shared = max(dev[a.device_id] if a.device_id else 1, card[getattr(a, "payment_fp", "")] if getattr(a, "payment_fp", "") else 1,
                     ip[a.ip_prefix] if a.ip_prefix else 1) - 1
        signals = []
        if shared:
            signals.append(f"shares a device, card or IP with {shared} other account{'s' if shared > 1 else ''}")
        if ss["orders"] >= 3 and ss["rate"] >= 0.25:
            signals.append(f"{round(ss['rate'] * 100)}% of their sales come back")
        if bs["orders"] >= 3 and bs["rate"] >= 0.25:
            signals.append(f"returns {round(bs['rate'] * 100)}% of what they buy")
        risk = min(1.0, (0.45 if shared >= 2 else 0.2 if shared else 0.0) + ss["rate"] * 0.6 + bs["rate"] * 0.6)
        rows.append({"id": a.id, "name": "You" if a.id == ME else a.name, "country": a.country,
                     "status": "frozen" if acct.frozen(a.id) else "active",
                     "reason": getattr(a, "suspend_reason", "") if acct.frozen(a.id) else "",
                     "sales": ss["orders"], "buys": bs["orders"], "seller_return_rate": ss["rate"],
                     "buyer_return_rate": bs["rate"], "owed": round(acct.cledger.total_unpaid(a.id), 2),
                     "risk": round(risk, 2), "signals": "; ".join(signals) or "no signals",
                     "paypal_payee": bool(acct.payee_for(a.id)), "me": a.id == ME})
    rows.sort(key=lambda r: (-r["risk"], -r["owed"]))
    return rows
