"""The control room's live event hub.

Every action a person takes in the control room (as a buyer, a creator or the operator) runs in a
worker thread with the tap attached. Each agent step, model token, PayPal call and guardrail it
produces is published here on that person's session channel, and every open control-room tab for
that session receives it over server-sent events. A short history lets a tab that joins late (or
reconnects) catch up.
"""
from __future__ import annotations

import queue
import threading
import time
from collections import defaultdict, deque


class LiveHub:
    def __init__(self, history: int = 600) -> None:
        self._subs: dict = defaultdict(list)
        self._hist: dict = defaultdict(lambda: deque(maxlen=history))
        self._busy: dict = defaultdict(int)
        self._lock = threading.Lock()

    def publish(self, sid: str, ev: dict) -> None:
        ev.setdefault("ts", round(time.time(), 3))
        with self._lock:
            self._hist[sid].append(ev)
            subs = list(self._subs[sid])
        for q in subs:
            try:
                q.put_nowait(ev)
            except Exception:
                pass

    def subscribe(self, sid: str):
        q: "queue.Queue" = queue.Queue(maxsize=5000)
        with self._lock:
            self._subs[sid].append(q)
            past = list(self._hist[sid])
        return q, past

    def unsubscribe(self, sid: str, q) -> None:
        with self._lock:
            if q in self._subs[sid]:
                self._subs[sid].remove(q)

    def busy(self, sid: str) -> int:
        with self._lock:
            return self._busy[sid]

    def mark(self, sid: str, delta: int) -> None:
        with self._lock:
            self._busy[sid] = max(0, self._busy[sid] + delta)


HUB = LiveHub()


def network(acct, max_creators: int = 22) -> dict:
    """The marketplace as a map for the control room: you, the busiest creators, the accounts the
    fraud engines have suspended, the platform and PayPal, with buyer-to-seller order edges. Ring
    links are NOT included: they appear only when a scan discovers them."""
    from marketplace.account import ME
    m = acct.market
    owed = {s: round(acct.cledger.total_unpaid(s), 2) for s in acct.sellers()}
    pick = [ME] + [s for s, _ in sorted(owed.items(), key=lambda kv: -kv[1]) if s != ME][:max_creators]
    pick += [a.id for a in m.accounts.values() if a.status != "active" or acct.frozen(a.id)]
    ids = list(dict.fromkeys(pick))
    sel = set(ids)
    edges: dict = {}
    for o in m.orders:
        if o.buyer in sel and o.seller in sel and o.buyer != o.seller:
            k = (o.buyer, o.seller)
            e = edges.setdefault(k, {"source": o.buyer, "target": o.seller, "count": 0, "amount": 0.0, "bad": 0})
            e["count"] += 1
            e["amount"] = round(e["amount"] + o.amount, 2)
            e["bad"] += o.status in ("returned", "charged_back")
    nodes = []
    for i in ids:
        a = m.accounts.get(i)
        if not a:
            continue
        nodes.append({"id": i, "name": "You" if i == ME else a.name, "country": a.country,
                      "owed": owed.get(i, 0.0), "frozen": bool(acct.frozen(i)), "me": i == ME,
                      "sales": sum(1 for o in m.orders if o.seller == i)})
    return {"nodes": nodes, "edges": list(edges.values())}


def books(snap: dict) -> dict:
    mk = snap.get("market") or {}
    return {"reserves": snap.get("reserves"), "liabilities": snap.get("liabilities"), "margin": snap.get("margin"),
            "solvent": snap.get("solvent"), "my_earnings": snap.get("my_earnings"),
            "frozen": mk.get("frozen_earnings"), "suspended": mk.get("suspended"),
            "orders": mk.get("orders"), "gmv_30d": mk.get("gmv_30d"),
            "advances": snap.get("advances_outstanding"), "receipts": snap.get("receipts"),
            "chain_intact": snap.get("chain_intact"), "holds": snap.get("open_holds") or [],
            "mandate": snap.get("mandate") or {}}
