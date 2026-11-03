"""Real market data for the reinvestment pool, so the NAV is not synthetic.

Pulls daily closes from the public Yahoo Finance chart endpoint (no key). Used
at generation time to embed a real-priced pool into the dashboard, and exposed
live through the MCP server's market_price tool. If the network is unavailable
the caller handles the exception; nothing here fabricates a price.
"""
from __future__ import annotations

_HEADERS = {"User-Agent": "Mozilla/5.0 (Helm market-data)"}
_BASE = "https://query1.finance.yahoo.com/v8/finance/chart/"


def fetch_history(ticker: str, rng: str = "6mo", interval: str = "1d") -> list[tuple[int, float]]:
    """Return [(unix_ts, close), ...] of real daily closes for a ticker."""
    import requests
    r = requests.get(f"{_BASE}{ticker}?range={rng}&interval={interval}",
                      headers=_HEADERS, timeout=20)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    ts = res["timestamp"]
    closes = res["indicators"]["quote"][0]["close"]
    return [(int(t), float(c)) for t, c in zip(ts, closes) if c is not None]


def latest_price(ticker: str) -> float:
    hist = fetch_history(ticker, rng="5d")
    if not hist:
        raise RuntimeError(f"no price for {ticker}")
    return round(hist[-1][1], 2)
