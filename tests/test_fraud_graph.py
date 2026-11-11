"""The graph-database fraud detector finds multi-hop rings and ignores non-links.

The decisive case is a ring whose members share NO single identifier but are chained across
several (device -> payment -> ip): a pairwise/GROUP BY approach never groups them, multi-hop
graph traversal does. We also assert a shared email domain is NOT treated as a link. The Kuzu
engine and the pure-Python fallback must return the same rings, so the capability is robust
whether or not the embedded graph database is installed.
"""
from __future__ import annotations

import os
import sys
from types import SimpleNamespace as Acct

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market.fraud_graph import FraudGraph


def _population():
    return [
        Acct(id="a", device_id="D1", payment_fp="",   ip_prefix="",        email_domain="gmail.com", bad_rate=0.6),
        Acct(id="b", device_id="D1", payment_fp="P1", ip_prefix="",        email_domain="yahoo.com", bad_rate=0.7),
        Acct(id="c", device_id="",   payment_fp="P1", ip_prefix="9.9.9.1", email_domain="gmail.com", bad_rate=0.5),
        Acct(id="d", device_id="",   payment_fp="",   ip_prefix="9.9.9.1", email_domain="live.com",  bad_rate=0.8),
        Acct(id="x", device_id="DX", payment_fp="PX", ip_prefix="1.1.1.1", email_domain="gmail.com", bad_rate=0.0),
        Acct(id="y", device_id="DY", payment_fp="PY", ip_prefix="2.2.2.2", email_domain="gmail.com", bad_rate=0.0),
    ]


def test_multi_hop_ring_is_found():
    out = FraudGraph().detect(_population())
    ring = next((r for r in out["rings"] if set(r["members"]) == {"a", "b", "c", "d"}), None)
    assert ring is not None, "the device->payment->ip chained ring was not detected"
    assert ring["multi_hop"] is True
    assert set(ring["kinds"]) == {"device", "payment", "ip"}
    assert ring["hops"] >= 3                       # a..b..c..d is three links


def test_shared_email_is_not_a_link():
    out = FraudGraph().detect(_population())
    # x and y share only a gmail domain; they must never be grouped into a ring
    assert not any({"x", "y"} <= set(r["members"]) for r in out["rings"])


def test_engine_and_fallback_agree():
    fg = FraudGraph()
    accts = _population()
    py_edges = fg._edges_via_python(accts)
    py_rings = {tuple(r.members) for r in fg._rings_from_edges(accts, py_edges)}
    if fg._kuzu is None:
        return                                     # engine not installed; fallback already covered above
    kz_edges = fg._edges_via_kuzu(accts)
    kz_rings = {tuple(r.members) for r in fg._rings_from_edges(accts, kz_edges)}
    assert kz_rings == py_rings                    # same rings with or without the graph database


def test_detect_on_generated_marketplace():
    from market.marketplace import generate_marketplace
    m = generate_marketplace(120, 7)
    out = FraudGraph().detect(list(m.accounts.values()))
    assert out["engine"] in ("kuzu", "python-fallback")
    assert out["accounts"] == len(m.accounts)
    assert isinstance(out["rings"], list)
    for r in out["rings"]:
        assert r["size"] >= 2 and 0.0 <= r["risk"] <= 1.0
