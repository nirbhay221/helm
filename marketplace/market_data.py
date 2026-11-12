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


def snapshot(ticker: str) -> dict:
    """Latest price plus what the last three months looked like: the return and how much it
    swung day to day (annualised volatility). Real closes; nothing is filled in."""
    hist = fetch_history(ticker, rng="3mo")
    if len(hist) < 5:
        raise RuntimeError(f"not enough history for {ticker}")
    closes = [c for _, c in hist]
    rets = [closes[i] / closes[i - 1] - 1 for i in range(1, len(closes))]
    mean = sum(rets) / len(rets)
    vol = (sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)) ** 0.5 * (252 ** 0.5)
    return {"ticker": ticker.upper(), "price": round(closes[-1], 2),
            "return_3m_pct": round((closes[-1] / closes[0] - 1) * 100, 1),
            "volatility_pct": round(vol * 100, 1)}


def news(tickers: list[str], limit: int = 12, env: dict | None = None) -> list[dict]:
    """The latest real headlines for these companies from Alpaca's market news feed (Benzinga).
    Needs the Alpaca keys; without them it raises rather than inventing news."""
    import os
    import requests
    env = env if env is not None else os.environ
    key, sec = env.get("ALPACA_API_KEY"), env.get("ALPACA_SECRET_KEY")
    if not (key and sec):
        raise RuntimeError("no Alpaca keys, so no news feed")
    r = requests.get("https://data.alpaca.markets/v1beta1/news",
                     params={"symbols": ",".join(t.upper() for t in tickers), "limit": int(limit)},
                     headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec}, timeout=20)
    r.raise_for_status()
    want = {t.upper() for t in tickers}
    return [{"time": n.get("created_at", "")[:16].replace("T", " "), "headline": n.get("headline", "")[:200],
             "symbols": [s for s in n.get("symbols", []) if s in want][:4], "source": n.get("source", "")}
            for n in r.json().get("news", [])]
