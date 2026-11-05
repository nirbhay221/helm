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

# strong identifiers only; email domain is deliberately excluded as noise
LINK_ATTRS = ("device_id", "payment_fp", "ip_prefix")


@dataclass
class Ring:
    id: str
    members: list = field(default_factory=list)      # account ids, sorted
    shared: dict = field(default_factory=dict)        # identifier -> shared value
    bad_rate: float = 0.0
    risk: float = 0.0
    action: str = "watch"                             # suspend_ring | watch
    reason: str = ""


class LinkageEngine:
    def __init__(self, min_shared: int = 2, min_ring: int = 2, suspend_risk: float = 0.5) -> None:
        self.min_shared = min_shared      # identifiers two accounts must share to link
        self.min_ring = min_ring          # accounts a component needs to be a ring
        self.suspend_risk = suspend_risk

    @staticmethod
    def _shared(a, b) -> dict:
        out = {}
        for attr in LINK_ATTRS:
            va, vb = getattr(a, attr, ""), getattr(b, attr, "")
            if va and va == vb:
                out[attr] = va
        return out

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

        # link any pair sharing >= min_shared strong identifiers
        for i in range(len(accs)):
            for j in range(i + 1, len(accs)):
                if len(self._shared(accs[i], accs[j])) >= self.min_shared:
                    union(accs[i].id, accs[j].id)

        groups: dict[str, list] = {}
        for a in accs:
            groups.setdefault(find(a.id), []).append(a.id)

        rings: list[Ring] = []
        for root, members in groups.items():
            if len(members) < self.min_ring:
                continue
            shared = {}
            for attr in LINK_ATTRS:
                vals = {getattr(m.accounts[x], attr, "") for x in members}
                if len(vals) == 1 and next(iter(vals)):
                    shared[attr] = next(iter(vals))
            bad = tot = 0
            for x in members:
                orders = m.orders_as_buyer(x) + m.orders_as_seller(x)
                tot += len(orders)
                bad += sum(1 for o in orders if o.status in ("returned", "charged_back"))
            rate = round(bad / tot, 3) if tot else 0.0
            density = len(shared) / len(LINK_ATTRS)
            risk = round(min(1.0, 0.5 * rate + 0.3 * density + 0.2 * min(1.0, len(members) / 5.0)), 3)
            action = "suspend_ring" if risk >= self.suspend_risk else "watch"
            reason = (f"{len(members)} accounts share {sorted(shared)} "
                      f"(bad-order rate {int(rate * 100)}%); inferred one coordinated actor. "
                      f"Risk {risk}. Action: {action}.")
            rings.append(Ring(id=f"ring-{root}", members=sorted(members), shared=shared,
                              bad_rate=rate, risk=risk, action=action, reason=reason))
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
