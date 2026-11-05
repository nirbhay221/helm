"""Real paper investing on live market prices (hole 3: no more pretend fund).

A creator can route a payout into investments and genuinely own a position. The
broker places FRACTIONAL buys at the real current price and marks the portfolio
to market on live prices, so gains and losses are real market movements, there is
just no real cash and no real security title. If Alpaca paper-trading keys are in
the environment it routes a real paper order through Alpaca; otherwise it books
the identical fill against the live price. Either way nothing is fabricated: the
price comes from the market.

Business shares (backing a shop or a restaurant) are a separate, clearly
simulated crowd-equity pool, because real equity needs a broker-dealer or a Reg CF
funding portal. That part is honest simulation with real pro-rata accounting.

Grounded in Alpaca's paper-trading API (real orders, live prices, fractional and
notional, no deposit) and standard mark-to-market portfolio accounting.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from .market_data import latest_price
from .reinvest import BASKET, Holding


def alpaca_ready(env: dict | None = None) -> bool:
    env = env if env is not None else os.environ
    return bool(env.get("ALPACA_API_KEY") and env.get("ALPACA_SECRET_KEY"))


class PaperBroker:
    """Executes fractional buys at the real current price. Routes a real Alpaca
    paper order when keys are present; otherwise books the same fill locally."""

    def __init__(self, price_fn=None, use_alpaca: bool | None = None, env: dict | None = None) -> None:
        self.env = env if env is not None else os.environ
        self.price_fn = price_fn or latest_price
        self.use_alpaca = alpaca_ready(self.env) if use_alpaca is None else use_alpaca

    @property
    def backend(self) -> str:
        return "alpaca-paper" if self.use_alpaca else "paper-live-price"

    def quote(self, ticker: str) -> float:
        return float(self.price_fn(ticker))

    def buy(self, ticker: str, notional: float) -> dict:
        px = self.quote(ticker)
        units = notional / px if px > 0 else 0.0
        routed = False
        if self.use_alpaca:
            routed = self._alpaca_order(ticker, notional)
        return {"ticker": ticker, "notional": round(float(notional), 2),
                "price": round(px, 2), "units": round(units, 6),
                "routed_to_alpaca": routed}

    def _alpaca_order(self, ticker: str, notional: float) -> bool:
        try:
            from alpaca.trading.client import TradingClient
            from alpaca.trading.enums import OrderSide, TimeInForce
            from alpaca.trading.requests import MarketOrderRequest
            client = TradingClient(self.env["ALPACA_API_KEY"], self.env["ALPACA_SECRET_KEY"], paper=True)
            client.submit_order(MarketOrderRequest(
                symbol=ticker, notional=round(float(notional), 2),
                side=OrderSide.BUY, time_in_force=TimeInForce.DAY))
            return True
        except Exception:
            return False


@dataclass
class Position:
    ticker: str
    units: float
    cost: float


@dataclass
class Portfolio:
    """One creator's real paper portfolio across the basket."""
    broker: PaperBroker
    positions: dict = field(default_factory=dict)      # ticker -> Position

    def invest(self, amount: float, basket: list[Holding] = BASKET) -> list[dict]:
        fills = []
        for h in basket:
            fill = self.broker.buy(h.ticker, amount * h.weight)
            p = self.positions.get(h.ticker)
            if p:
                p.units += fill["units"]
                p.cost += fill["notional"]
            else:
                self.positions[h.ticker] = Position(h.ticker, fill["units"], fill["notional"])
            fills.append(fill)
        return fills

    def market_value(self) -> float:
        return round(sum(pos.units * self.broker.quote(t) for t, pos in self.positions.items()), 2)

    def cost_basis(self) -> float:
        return round(sum(p.cost for p in self.positions.values()), 2)

    def return_pct(self) -> float:
        c = self.cost_basis()
        return round((self.market_value() - c) / c * 100.0, 2) if c else 0.0


@dataclass
class Business:
    """A shop or restaurant creators can back for a pro-rata share. Simulated
    crowd-equity: real pro-rata ownership, modeled business performance."""
    name: str
    kind: str                         # "shop" | "restaurant" | "studio"
    target: float
    monthly_return: float = 0.0       # modeled performance of the business
    raised: float = 0.0
    backers: dict = field(default_factory=dict)   # creator -> contributed

    def back(self, creator: str, amount: float) -> float:
        amount = min(float(amount), max(0.0, self.target - self.raised))
        if amount <= 0:
            return 0.0
        self.raised += amount
        self.backers[creator] = self.backers.get(creator, 0.0) + amount
        return round(amount, 2)

    def share_of(self, creator: str) -> float:
        return round(self.backers.get(creator, 0.0) / self.raised, 4) if self.raised else 0.0

    def value_for(self, creator: str, months: int = 1) -> float:
        contributed = self.backers.get(creator, 0.0)
        return round(contributed * ((1.0 + self.monthly_return) ** months), 2)
