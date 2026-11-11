"""Helm trust MCP server: the marketplace trust-and-safety domain, over MCP.

Exposes the two-sided abuse engine and the fraud-ring linkage engine as agent
tools. Fully deterministic and offline (no keys, no network): the judgment is the
deterministic part, correctly, while the agentic world that generates the
behaviour lives elsewhere.
"""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from market.a2a import check_deal
from market.abuse import AbuseEngine
from market.knowledge import retrieve, topics
from market.linkage import LinkageEngine
from market.marketplace import generate_marketplace
from marketplace.tax import regime_for


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

    @server.tool(
        name="tax_regime",
        description=("Determine a creator's reporting regime from their country, gross sales, "
                     "transaction count and fees: US 1099-K (gross and threshold) or EU DAC7 "
                     "(consideration and de-minimis). Figures only, deterministic."),
    )
    def tax_regime(country: str, gross: float, transactions: int, fees: float = 0.0) -> dict:
        return regime_for(country, float(gross), int(transactions), float(fees))

    @server.tool(
        name="a2a_check",
        description=("Verify a signed owner mandate (a verifiable credential) and decide whether a "
                     "proposed agent-to-agent deal is allowed, without moving money. Returns whether "
                     "the mandate verified, whether the deal fits the caps, and whether it needs the "
                     "owner's approval. An over-threshold deal needs a signed cart mandate."),
    )
    def a2a_check(intent_credential: dict, category: str, price: float, spent: float = 0.0,
                  cart_credential: dict = None) -> dict:
        return check_deal(intent_credential, category, float(price), float(spent), cart_credential)

    @server.tool(
        name="financial_knowledge",
        description=("Ground an agent before it decides: retrieve the relevant financial "
                     "principles (expected loss PD x LGD x EAD, CECL provisioning, large-exposure "
                     "caps, RAROC pricing, conformal uncertainty, spend-authority, prompt-injection, "
                     "tax thresholds) for a query. Any agent, Helm's or an external one, can pull "
                     "the same grounding so its reasoning is financially literate, not generic."),
    )
    def financial_knowledge(query: str, k: int = 4) -> dict:
        items = retrieve(str(query), int(k))
        return {"query": query,
                "principles": [{"topic": p.topic, "statement": p.statement, "source": p.source}
                               for p in items],
                "available_topics": topics()}

    return server
