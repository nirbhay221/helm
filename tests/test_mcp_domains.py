"""The domain MCP servers expose their tools and enforce the real logic over MCP.

Offline: the trust server needs no keys or network; the market server's tool list
and the offline business tool are exercised (live-price tools need the network,
so they are not called here)."""
from __future__ import annotations

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server.market_server import build_market_server  # noqa: E402
from mcp_server.trust_server import build_trust_server  # noqa: E402


def _json(result):
    return json.loads(result.content[0].text)


def test_trust_server_scans_rings_over_mcp():
    server = build_trust_server()
    names = {t.name for t in asyncio.run(server.list_tools())}
    assert {"scan_abuse", "scan_rings"} <= names
    out = _json(asyncio.run(server.call_tool("scan_rings", {"n_accounts": 120, "seed": 7})))
    assert len(out["rings"]) == 2                       # the two inferred rings
    assert all(r["risk"] >= 0.5 for r in out["rings"])


def test_market_server_exposes_tools_and_backs_a_business():
    server = build_market_server()
    names = {t.name for t in asyncio.run(server.list_tools())}
    assert {"market_quote", "invest_payout", "back_business"} <= names
    out = _json(asyncio.run(server.call_tool("back_business", {
        "name": "Lagos Coffee", "kind": "restaurant", "target": 1000.0,
        "amount": 600.0, "creator": "Ava", "monthly_return": 0.02})))
    assert out["backed"] == 600.0 and abs(out["share"] - 1.0) < 1e-6   # sole backer so far
