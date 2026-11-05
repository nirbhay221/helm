"""Helm trust MCP server: the marketplace trust-and-safety domain, over MCP.

Exposes the two-sided abuse engine and the fraud-ring linkage engine as agent
tools. Fully deterministic and offline (no keys, no network): the judgment is the
deterministic part, correctly, while the agentic world that generates the
behaviour lives elsewhere.
"""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from market.abuse import AbuseEngine
from market.linkage import LinkageEngine
from market.marketplace import generate_marketplace


def build_trust_server() -> MCPServer:
    server = MCPServer("helm-trust")

    @server.tool(
        name="scan_abuse",
        description=("Scan a seeded two-sided marketplace for abuse and attribute fault: a "
                     "serial-returner buyer (returns spread across many sellers) versus a bad "
                     "seller (returns spread across many buyers). Returns the verdicts."),
    )
    def scan_abuse(n_accounts: int = 120, seed: int = 7) -> dict:
        m = generate_marketplace(int(n_accounts), int(seed))
        return {"verdicts": [{"name": v.name, "role": v.role, "bad": v.bad_count,
                              "distinct": v.distinct_counterparties, "rate": v.rate,
                              "action": v.action} for v in AbuseEngine(min_bad=10).scan(m)]}

    @server.tool(
        name="scan_rings",
        description=("Infer fraud rings from shared identity signals (device, payment "
                     "fingerprint, IP) without being told who is linked. Returns each ring, the "
                     "signals it shares, its bad-order rate and a risk score."),
    )
    def scan_rings(n_accounts: int = 120, seed: int = 7) -> dict:
        m = generate_marketplace(int(n_accounts), int(seed))
        return {"rings": [{"members": r.members, "shared": r.shared, "bad_rate": r.bad_rate,
                           "risk": r.risk, "action": r.action, "reason": r.reason}
                          for r in LinkageEngine().infer(m)]}

    return server
