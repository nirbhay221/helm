"""Helm as an MCP server: its capabilities exposed over the Model Context Protocol.

PayPal ships an official MCP server (orders, invoices, subscriptions, disputes),
but it has no tool for paying out. Helm fills exactly that gap and adds the two
capabilities that make it a controller rather than a wrapper: the sourcing
optimizer and the AI signal desk. Any MCP client (Claude Desktop, Cursor, an
agent runtime) can connect over stdio and call:

  paypal_create_payout - send a PayPal Payouts batch, AUP-gated, idempotent, and
                         held for human approval above a threshold. Runs live
                         against the sandbox when credentials are present,
                         otherwise a labeled demo response.
  source_suppliers     - the cheapest supplier split for a target quantity under
                         MOQ, capacity and all-units quantity discounts (a MILP).
  interpret_signal     - read an unstructured operational signal (a promo note, a
                         supplier delay) with a panel of models and return a
                         bounded demand adjustment with a confidence from model
                         agreement. The model informs; it never sets a quantity.

The money-moving tool keeps every guard it has in-process; MCP is only the
transport. Secrets come from the environment, never from tool arguments.
"""
from __future__ import annotations

import os

from mcp.server.mcpserver import MCPServer

from agent import LLMClient, SignalDesk
from arms.awardsmith import AwardsmithSolver, DiscountTier, SupplierQuote, naive_single_supplier_cost
from paypal import Ledger, PayPalClient
from paypal.mcp_payouts_tool import run_payouts_tool

# A small panel of tool-calling models; the signal desk uses whatever responds.
SIGNAL_PANEL = [
    "qwen/qwen-2.5-72b-instruct",
    "deepseek/deepseek-chat",
    "meta-llama/llama-3.3-70b-instruct",
]


def build_server() -> MCPServer:
    server = MCPServer("helm")

    # Shared, server-held PayPal client + ledger. Credentials from the env only.
    _client = PayPalClient(env=os.environ)
    _ledger = Ledger()

    @server.tool(
        name="paypal_create_payout",
        description=(
            "Send a PayPal Payouts batch to recipients by email. Only AUP-permitted "
            "purposes (COMMISSION, REBATE, REWARD, INCENTIVE) are allowed; payroll and "
            "paying suppliers for goods are refused. Idempotent on sender_batch_id. "
            "Batches above the approval threshold are held until approved=true."
        ),
    )
    def paypal_create_payout(
        sender_batch_id: str,
        purpose: str,
        recipients: list[dict],
        currency: str = "USD",
        approved: bool = False,
    ) -> dict:
        return run_payouts_tool(
            {
                "sender_batch_id": sender_batch_id,
                "purpose": purpose,
                "recipients": recipients,
                "currency": currency,
                "approved": approved,
            },
            client=_client,
            ledger=_ledger,
        )

    @server.tool(
        name="source_suppliers",
        description=(
            "Find the cheapest way to buy target_qty units across suppliers under "
            "minimum order quantities, capacity, and all-units quantity discounts. "
            "Each supplier is {name, capacity, tiers:[[min_qty, unit_price], ...], "
            "fixed_cost?}. Returns the optimal split, its cost, and the saving versus "
            "putting the whole order with the cheapest single supplier."
        ),
    )
    def source_suppliers(target_qty: float, suppliers: list[dict]) -> dict:
        quotes = [
            SupplierQuote(
                name=s["name"],
                tiers=[DiscountTier(float(t[0]), float(t[1])) for t in s.get("tiers", [])],
                capacity=float(s.get("capacity", 0.0)),
                fixed_cost=float(s.get("fixed_cost", 0.0)),
            )
            for s in suppliers
        ]
        res = AwardsmithSolver(quotes).allocate(float(target_qty))
        naive = naive_single_supplier_cost(quotes, float(target_qty))
        return {
            "status": res.status,
            "total_cost": res.total_cost,
            "total_quantity": res.total_quantity,
            "lines": [{"supplier": l.supplier, "quantity": l.quantity,
                       "unit_price": l.unit_price, "line_cost": l.line_cost}
                      for l in res.lines],
            "naive_single_supplier_cost": None if naive == float("inf") else naive,
            "saving": None if naive == float("inf") else round(naive - res.total_cost, 2),
        }

    @server.tool(
        name="interpret_signal",
        description=(
            "Read an unstructured operational signal (free text) and return the "
            "demand change it implies as per-period deltas, using a panel of models. "
            "Includes a confidence derived from how much the models agree; a vague or "
            "incoherent signal yields a small or empty adjustment. Never returns an "
            "order quantity."
        ),
    )
    def interpret_signal(
        signal_text: str,
        current_period: int = 0,
        baseline_demand: float = 20.0,
        horizon: int = 8,
    ) -> dict:
        desk = SignalDesk(LLMClient(env=os.environ), models=SIGNAL_PANEL)
        adj = desk.interpret(signal_text, current_period=int(current_period),
                             baseline_demand=float(baseline_demand), horizon=int(horizon))
        return {
            "period_deltas": {int(k): round(v, 2) for k, v in adj.period_deltas.items()},
            "rationale": adj.rationale,
            "cited_signal": adj.cited_signal,
            "disagreement": adj.disagreement,
            "confidence": adj.confidence,
            "source": adj.source,
            "model_votes": adj.model_votes,
        }

    return server


def main() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
    except Exception:
        pass
    build_server().run(transport="stdio")


if __name__ == "__main__":
    main()
