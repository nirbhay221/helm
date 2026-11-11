"""Helm's MCP server exposes its tools and keeps every guard over the protocol.

Keyless and demo-mode (DEMO_MODE=1 is forced, so no live PayPal or model call).
Exercises the real MCPServer via list_tools / call_tool.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DEMO_MODE"] = "1"          # force demo: never touch live PayPal in tests

from mcp_server.server import build_server  # noqa: E402


def _json(result):
    return json.loads(result.content[0].text)


def _call(server, name, args):
    return asyncio.run(server.call_tool(name, args))


def test_server_exposes_expected_tools():
    server = build_server()
    names = {t.name for t in asyncio.run(server.list_tools())}
    assert {"paypal_create_payout", "interpret_signal", "market_price"} <= names


def test_payout_tool_runs_in_demo_and_enforces_aup_over_mcp():
    server = build_server()
    ok = _json(_call(server, "paypal_create_payout", {
        "sender_batch_id": "test-mcp-ok", "purpose": "COMMISSION",
        "recipients": [{"email": "a@ex.com", "amount": 25.0, "note": "commission"}],
    }))
    assert ok["status"] == "completed"
    assert ok["batch_id"]
    assert ok["demo"] is True

    bad = _json(_call(server, "paypal_create_payout", {
        "sender_batch_id": "test-mcp-bad", "purpose": "PAYROLL",
        "recipients": [{"email": "b@ex.com", "amount": 25.0}],
    }))
    assert bad["status"] == "rejected"      # the AUP guard holds over the protocol
