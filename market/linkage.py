"""Infer fraud rings from shared identity signals, never from a label.

This is the real version of sybil detection. A real platform cannot see "these
accounts are one person"; it sees signals (device fingerprint, payment
instrument, IP block, signup time) and must infer coordination. We build the
standard shared-attribute graph: accounts are nodes, an edge joins two accounts
that share two or more STRONG identifiers (one shared identifier, like a common
email domain or a shared household IP, is noise), and a connected component of
that graph is a candidate ring. Each ring is scored by its members' bad-order
rate, how many identifiers the whole ring has in common, and its size.

Grounded in the fraud-ring literature: model accounts as nodes and shared
attributes as edges, take connected components, and treat two shared attributes
as a far stronger signal than one (Liu 2025, arXiv 2512.19061; and the standard
connected-components baseline). The inferred ring id then replaces the
ground-truth cluster label the payout hardening used to be handed.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .marketplace import Marketplace

# identifiers weighted by how strong a signal they are. Device and payment
# fingerprints are strong; an IP block is medium; a shared email domain is weak
# (many honest people share gmail). Links form on TOTAL weight, so weak signals
# combine, and a ring that rotates one identifier still links on the others.
ATTR_WEIGHT = {"device_id": 1.0, "payment_fp": 1.0, "ip_prefix": 0.6, "email_domain": 0.3}
LINK_THRESHOLD = 1.5                 # total shared-signal weight to join two accounts
BURST_WINDOW = 7                     # signups this close together look coordinated


@dataclass
class Ring:
    id: str
    members: list = field(default_factory=list)      # account ids, sorted
    shared: dict = field(default_factory=dict)        # identifier -> shared value
    bad_rate: float = 0.0
    signup_window: int = 0                            # day-spread of the ring's signups
    burst: bool = False                               # signed up within BURST_WINDOW
    risk: float = 0.0
    action: str = "watch"                             # suspend_ring | watch
    reason: str = ""


class LinkageEngine:
    def __init__(self, link_threshold: float = LINK_THRESHOLD, min_ring: int = 2,
                 suspend_risk: float = 0.5, burst_window: int = BURST_WINDOW) -> None:
        self.link_threshold = link_threshold
        self.min_ring = min_ring
        self.suspend_risk = suspend_risk
        self.burst_window = burst_window

    @staticmethod
    def _link_weight(a, b) -> tuple[float, dict]:
        weight, shared = 0.0, {}
        for attr, w in ATTR_WEIGHT.items():
            va, vb = getattr(a, attr, ""), getattr(b, attr, "")
            if va and va == vb:
                weight += w
                shared[attr] = va
        # fuzzy: same leading IP block even if the full prefix differs (rotation)
        ia, ib = getattr(a, "ip_prefix", ""), getattr(b, "ip_prefix", "")
        if ia and ib and ia != ib and ia.rsplit(".", 1)[0] == ib.rsplit(".", 1)[0]:
            weight += 0.3
        return weight, shared

    def infer(self, m: Marketplace) -> list[Ring]:
        accs = list(m.accounts.values())
        parent = {a.id: a.id for a in accs}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x, y):
            parent[find(x)] = find(y)

        for i in range(len(accs)):
            for j in range(i + 1, len(accs)):
                w, _ = self._link_weight(accs[i], accs[j])
                if w >= self.link_threshold:
                    union(accs[i].id, accs[j].id)

        groups: dict[str, list] = {}
        for a in accs:
            groups.setdefault(find(a.id), []).append(a.id)

        rings: list[Ring] = []
        for root, members in groups.items():
            if len(members) < self.min_ring:
                continue
            shared = {}
            for attr in ATTR_WEIGHT:
                vals = {getattr(m.accounts[x], attr, "") for x in members}
                if len(vals) == 1 and next(iter(vals)):
                    shared[attr] = next(iter(vals))
            bad = tot = 0
            for x in members:
                orders = m.orders_as_buyer(x) + m.orders_as_seller(x)
                tot += len(orders)
                bad += sum(1 for o in orders if o.status in ("returned", "charged_back"))
            rate = round(bad / tot, 3) if tot else 0.0
            days = [m.accounts[x].joined_day for x in members]
            window = max(days) - min(days) if days else 0
            burst = window <= self.burst_window
            # weight the shared signals by strength, not just count
            density = min(1.0, sum(ATTR_WEIGHT.get(k, 0.0) for k in shared) / 2.0)
            risk = round(min(1.0, 0.45 * rate + 0.20 * density
                             + 0.15 * min(1.0, len(members) / 5.0)
                             + 0.20 * (1.0 if burst else 0.0)), 3)
            action = "suspend_ring" if risk >= self.suspend_risk else "watch"
            reason = (f"{len(members)} accounts share {sorted(shared)}"
                      f"{', signed up within ' + str(window) + ' days' if burst else ''} "
                      f"(bad-order rate {int(rate * 100)}%); inferred one coordinated actor. "
                      f"Risk {risk}. Action: {action}.")
            rings.append(Ring(id=f"ring-{root}", members=sorted(members), shared=shared,
                              bad_rate=rate, signup_window=window, burst=burst,
                              risk=risk, action=action, reason=reason))
        rings.sort(key=lambda r: r.risk, reverse=True)
        return rings

    def cluster_of(self, m: Marketplace) -> dict:
        """Map each account to its inferred ring id (or its own id if unlinked),
        so the payout hardening merges identities it INFERRED, not ones it was told."""
        label = {aid: aid for aid in m.accounts}
        for r in self.infer(m):
            for x in r.members:
                label[x] = r.id
        return label
