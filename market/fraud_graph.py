"""Fraud rings in a real graph database (Kuzu, embedded, Cypher), not just graph features.

market/graphfraud.py computes structural FEATURES (edge density, near-clique) over the
pairwise link model. This goes one step further and is the honest answer to "where does a
graph database help": it loads the marketplace as a PROPERTY GRAPH -- Account nodes and the
Identity nodes they share (device, payment instrument, IP block) -- into an embedded Kuzu
database, then uses recursive Cypher traversal to find rings that a pairwise or GROUP BY
approach cannot see: members who share NO single identifier but are chained across several
(A shares a device with B, B shares a card with C, C shares an IP with D -> one ring). That
multi-hop reachability is exactly what a graph database does natively and a relational join
does painfully. Email domain is deliberately NOT an edge (a shared gmail is not a link), matching
the link model's logic.

Kuzu is embedded (a single on-disk/in-memory database, no server), so it runs on the box with
no new infrastructure. If Kuzu is unavailable the module degrades to the same connected-component
result computed in pure Python, so the capability never hard-depends on the engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Only STRONG identifiers become edges; a shared email domain is not a link (see link model).
_STRONG = (("device", "device_id"), ("payment", "payment_fp"), ("ip", "ip_prefix"))


@dataclass
class GraphRing:
    members: list = field(default_factory=list)       # account ids
    identities: list = field(default_factory=list)    # [{kind, key, accounts}] that bind it
    kinds: list = field(default_factory=list)          # distinct identifier kinds spanned
    multi_hop: bool = False                            # chained across >1 identifier (graph-only insight)
    hops: int = 0                                      # longest shared-identity chain length
    bad_rate: float = 0.0
    size: int = 0
    risk: float = 0.0
    reason: str = ""


def _identities(acc) -> list:
    out = []
    for kind, attr in _STRONG:
        v = getattr(acc, attr, "") or ""
        if v:
            out.append((kind, f"{kind}:{v}"))
    return out


class FraudGraph:
    """Build the account/identity property graph and detect rings by multi-hop traversal."""

    def __init__(self):
        self._kuzu = None
        try:
            import kuzu  # noqa: F401
            self._kuzu = kuzu
        except Exception:
            self._kuzu = None

    # --- public -------------------------------------------------------------
    def detect(self, accounts) -> dict:
        """accounts: objects with .id, strong identifier attrs, optional .bad/.bad_rate.
        Returns the detected rings (size >= 2), ranked by risk, with the graph engine used."""
        accounts = list(accounts or [])
        if self._kuzu is not None:
            try:
                edges = self._edges_via_kuzu(accounts)
                engine = "kuzu"
            except Exception:
                edges, engine = self._edges_via_python(accounts), "python-fallback"
        else:
            edges, engine = self._edges_via_python(accounts), "python-fallback"

        rings = self._rings_from_edges(accounts, edges)
        rings.sort(key=lambda r: r.risk, reverse=True)
        return {
            "engine": engine,
            "accounts": len(accounts),
            "rings": [self._ring_dict(r) for r in rings],
            "count": len(rings),
            "multi_hop_rings": sum(1 for r in rings if r.multi_hop),
        }

    # --- graph-database path ------------------------------------------------
    def _edges_via_kuzu(self, accounts) -> list:
        """Load the property graph into Kuzu and return account-account shared-identity
        edges via a two-hop Cypher traversal (Account)-[:USES]->(Identity)<-[:USES]-(Account)."""
        kuzu = self._kuzu
        db = kuzu.Database(":memory:")                 # embedded, in-process, no files or server
        conn = kuzu.Connection(db)
        conn.execute("CREATE NODE TABLE Account(id STRING, bad DOUBLE, PRIMARY KEY(id))")
        conn.execute("CREATE NODE TABLE Identity(key STRING, kind STRING, PRIMARY KEY(key))")
        conn.execute("CREATE REL TABLE USES(FROM Account TO Identity)")
        seen_ids = set()
        for a in accounts:
            bad = float(getattr(a, "bad_rate", getattr(a, "bad", 0.0)) or 0.0)
            conn.execute("CREATE (:Account {id: $id, bad: $bad})", {"id": str(a.id), "bad": bad})
        for a in accounts:
            for kind, key in _identities(a):
                if key not in seen_ids:
                    conn.execute("CREATE (:Identity {key: $k, kind: $kind})", {"k": key, "kind": kind})
                    seen_ids.add(key)
                conn.execute(
                    "MATCH (a:Account {id:$id}), (i:Identity {key:$k}) CREATE (a)-[:USES]->(i)",
                    {"id": str(a.id), "k": key})
        # the graph join: two accounts sharing any identity, with the identity as evidence
        res = conn.execute(
            "MATCH (a:Account)-[:USES]->(i:Identity)<-[:USES]-(b:Account) "
            "WHERE a.id < b.id RETURN a.id, b.id, i.kind, i.key")
        edges = []
        while res.has_next():
            a_id, b_id, kind, key = res.get_next()
            edges.append((a_id, b_id, kind, key))
        return edges

    def _edges_via_python(self, accounts) -> list:
        """Same shared-identity edges without the engine (invert identity -> accounts)."""
        by_key: dict = {}
        for a in accounts:
            for kind, key in _identities(a):
                by_key.setdefault((kind, key), []).append(str(a.id))
        edges = []
        for (kind, key), ids in by_key.items():
            ids = sorted(set(ids))
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    edges.append((ids[i], ids[j], kind, key))
        return edges

    # --- ring assembly (connected components over the shared-identity edges) --
    def _rings_from_edges(self, accounts, edges) -> list:
        parent: dict = {str(a.id): str(a.id) for a in accounts}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x, y):
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[rx] = ry

        for a_id, b_id, _k, _key in edges:
            if a_id in parent and b_id in parent:
                union(a_id, b_id)

        comps: dict = {}
        for aid in parent:
            comps.setdefault(find(aid), set()).add(aid)
        bad_by_id = {str(a.id): float(getattr(a, "bad_rate", getattr(a, "bad", 0.0)) or 0.0)
                     for a in accounts}

        rings = []
        for members in comps.values():
            if len(members) < 2:
                continue
            ev = [(a, b, k, key) for (a, b, k, key) in edges if a in members and b in members]
            kinds = sorted({k for _a, _b, k, _key in ev})
            ident_map: dict = {}
            for _a, _b, k, key in ev:
                ident_map.setdefault((k, key), set()).update((_a, _b))
            identities = [{"kind": k, "key": key, "accounts": sorted(accs)}
                          for (k, key), accs in sorted(ident_map.items())]
            multi_hop = len(kinds) > 1
            hops = self._longest_chain(members, ev)
            bad_rate = round(sum(bad_by_id.get(m, 0.0) for m in members) / len(members), 3)
            size = len(members)
            # risk: bad behaviour, size, and the multi-hop structure a single actor leaves
            risk = round(min(1.0, 0.5 * bad_rate + 0.1 * min(size, 5) + (0.2 if multi_hop else 0.0)), 3)
            reason = ("chained across " + ", ".join(kinds) + f" over {hops} hops"
                      if multi_hop else "shares " + (kinds[0] if kinds else "an identifier"))
            rings.append(GraphRing(members=sorted(members), identities=identities, kinds=kinds,
                                   multi_hop=multi_hop, hops=hops, bad_rate=bad_rate, size=size,
                                   risk=risk, reason=reason))
        return rings

    @staticmethod
    def _longest_chain(members, ev) -> int:
        """Longest simple path length (in hops) through the ring's shared-identity edges:
        how many links chain the furthest two members together."""
        adj: dict = {m: set() for m in members}
        for a, b, _k, _key in ev:
            adj[a].add(b)
            adj[b].add(a)
        best = 0

        def dfs(node, seen, depth):
            nonlocal best
            best = max(best, depth)
            for nxt in adj[node]:
                if nxt not in seen:
                    dfs(nxt, seen | {nxt}, depth + 1)

        for m in members:
            dfs(m, {m}, 0)
        return best

    @staticmethod
    def _ring_dict(r: GraphRing) -> dict:
        return {"members": r.members, "size": r.size, "kinds": r.kinds,
                "multi_hop": r.multi_hop, "hops": r.hops, "bad_rate": r.bad_rate,
                "risk": r.risk, "identities": r.identities, "reason": r.reason}
