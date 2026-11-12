"""Helm market MCP server: the investing domain, over MCP.

Split out from the payouts server by domain (the 2026 consensus: one bounded
context per server, a handful of tools each, namespaced). Exposes the real paper
broker, live market quotes, investing a payout across the basket at live prices,
and backing a creator business for a pro-rata share. Secrets (Alpaca keys) come
from the environment; when present, buys route as real Alpaca paper orders.
"""
from __future__ import annotations

import os

from mcp.server.mcpserver import MCPServer

from marketplace.invest import Business, PaperBroker, Portfolio, Property


def build_market_server() -> MCPServer:
    server = MCPServer("helm-market")
    broker = PaperBroker(env=os.environ)

    @server.tool(
        name="market_quote",
        description=("Latest real market price for a ticker (e.g. SPY, VNQ, MCD). Real data "
                     "from a public market endpoint; returns an error field if unreachable."),
    )
    def market_quote(ticker: str) -> dict:
        try:
            return {"ticker": ticker.upper(), "price": broker.quote(ticker), "backend": broker.backend}
        except Exception as exc:
            return {"ticker": ticker.upper(), "error": str(exc)[:120]}

    @server.tool(
        name="market_snapshot",
        description=("For each ticker: the latest real price, the 3-month return and the annualised "
                     "day-to-day volatility, from real daily closes. A failed ticker carries an error field."),
    )
    def market_snapshot(tickers: list[str]) -> dict:
        from marketplace.market_data import snapshot
        out = []
        for t in tickers[:15]:
            try:
                out.append(snapshot(t))
            except Exception as exc:
                out.append({"ticker": t.upper(), "error": str(exc)[:120]})
        return {"snapshots": out}

    @server.tool(
        name="market_news",
        description=("The latest real news headlines for these companies (Alpaca market news, Benzinga), "
                     "newest first, with the time and which of the tickers each one mentions."),
    )
    def market_news(tickers: list[str], limit: int = 12) -> dict:
        from marketplace.market_data import news
        try:
            return {"news": news(tickers, limit)}
        except Exception as exc:
            return {"news": [], "error": str(exc)[:160]}

    @server.tool(
        name="invest_payout",
        description=("Invest a notional dollar amount across the basket (US stocks, real estate, "
                     "restaurants) at live prices. Returns the fractional-unit fills, the cost "
                     "basis, the live market value, and whether it routed to Alpaca paper."),
    )
    def invest_payout(amount: float) -> dict:
        pf = Portfolio(broker)
        fills = pf.invest(float(amount))
        return {"backend": broker.backend, "fills": fills,
                "cost_basis": pf.cost_basis(), "market_value": pf.market_value()}

    @server.tool(
        name="back_business",
        description=("Back a creator business (shop, restaurant or studio) for a pro-rata share. "
                     "Simulated crowd-equity with real pro-rata accounting; amount is capped at "
                     "the remaining target."),
    )
    def back_business(name: str, kind: str, target: float, amount: float,
                      creator: str, monthly_return: float = 0.0) -> dict:
        b = Business(name, kind, float(target), float(monthly_return))
        got = b.back(creator, float(amount))
        return {"business": name, "backed": got, "share": b.share_of(creator),
                "value_1mo": b.value_for(creator, 1)}

    @server.tool(
        name="back_property",
        description=("Buy a fractional share of a property together with other creators. Returns the "
                     "amount invested, the pro-rata share, and the projected one-year value. Illiquid, "
                     "multi-year hold; simulated with real-world yield and appreciation."),
    )
    def back_property(name: str, location: str, value: float, amount: float, creator: str,
                      rent_yield_annual: float = 0.05, appreciation_annual: float = 0.04) -> dict:
        p = Property(name, location, float(value), rent_yield_annual=float(rent_yield_annual),
                     appreciation_annual=float(appreciation_annual))
        got = p.buy(creator, float(amount))
        return {"property": name, "location": location, "invested": got,
                "share": p.share_of(creator), "value_1yr": p.value_for(creator, 12), "note": p.note}

    return server
