"""The reinvestment pool: creators keep their payout in and own a real-priced slice.

Instead of withdrawing, a creator can route a payout into a pooled fund. The pool
holds a fixed basket of real, liquid assets (a broad stock ETF, a real-estate
ETF, and a restaurant-chain stock, the things the idea named). A contribution
buys UNITS at the current net asset value; the creator's stake is units times
NAV, so ownership is exactly proportional to money put in, and it moves with the
real market. This is the same pro-rata unit accounting a real pooled vehicle
uses; here it is priced on real market data but no real securities are bought.

SANDBOX CONCEPT: a licensed version is a regulated securities offering (Reg CF /
an SPV with a custodian, a broker-dealer or funding portal, money-transmitter
licensing). This models the mechanics and the engagement loop, not a live fund.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Holding:
    ticker: str
    label: str
    weight: float          # target weight in the basket (weights sum to 1)


# The basket the idea described: stocks, homes (real estate), restaurant chains.
BASKET = [
    Holding("SPY", "US stocks (S&P 500 ETF)", 0.50),
    Holding("VNQ", "real estate / homes (REIT ETF)", 0.30),
    Holding("MCD", "restaurant chains (McDonald's)", 0.20),
]


def nav_series(histories: dict[str, list[tuple[int, float]]],
               basket: list[Holding] = BASKET) -> tuple[list[int], list[float]]:
    """A weighted basket index rebased to 100 at the start, from real closes.

    histories maps ticker -> [(ts, close), ...]. Aligns on the shortest common
    length (most recent N points) so the weighting is consistent."""
    series = {h.ticker: [c for _, c in histories[h.ticker]] for h in basket}
    stamps = {h.ticker: [t for t, _ in histories[h.ticker]] for h in basket}
    n = min(len(v) for v in series.values())
    series = {k: v[-n:] for k, v in series.items()}
    dates = stamps[basket[0].ticker][-n:]
    base = {h.ticker: series[h.ticker][0] for h in basket}
    nav = []
    for i in range(n):
        idx = sum(h.weight * (series[h.ticker][i] / base[h.ticker]) for h in basket)
        nav.append(round(100.0 * idx, 4))
    return dates, nav


@dataclass
class ReinvestmentPool:
    dates: list[int]
    nav: list[float]                 # NAV per unit over time (starts at 100)
    contributions: list[dict] = field(default_factory=list)  # {creator, amount, at, units}

    @property
    def nav_now(self) -> float:
        return self.nav[-1]

    def contribute(self, creator: str, amount: float, at: int = 0) -> float:
        """Route `amount` in at the NAV on day `at`; returns units issued."""
        nav_at = self.nav[at]
        units = amount / nav_at if nav_at > 0 else 0.0
        self.contributions.append({"creator": creator, "amount": round(amount, 2),
                                   "at": at, "units": round(units, 6)})
        return units

    def stake_value(self, creator: str) -> float:
        units = sum(c["units"] for c in self.contributions if c["creator"] == creator)
        return round(units * self.nav_now, 2)

    def contributed(self, creator: str) -> float:
        return round(sum(c["amount"] for c in self.contributions if c["creator"] == creator), 2)

    def total_units(self) -> float:
        return round(sum(c["units"] for c in self.contributions), 6)

    def total_contributed(self) -> float:
        return round(sum(c["amount"] for c in self.contributions), 2)

    def total_value(self) -> float:
        return round(self.total_units() * self.nav_now, 2)
