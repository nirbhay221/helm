"""Build the reinvestment pool from real market data and embed it.

Fetches six months of real daily closes for the basket (needs network), builds
the NAV series, simulates the slice of creators who chose to reinvest their
payout at the start, and saves ui/reinvest_data.json for the dashboard. Prices
are real; no securities are actually bought (sandbox concept). Re-run to refresh.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marketplace.allocator import make_global_creators
from marketplace.market_data import fetch_history
from marketplace.reinvest import BASKET, ReinvestmentPool, nav_series

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui", "reinvest_data.json")


def main() -> None:
    histories = {h.ticker: fetch_history(h.ticker, rng="6mo") for h in BASKET}
    dates, nav = nav_series(histories)
    date_labels = [dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%d") for t in dates]

    holdings = []
    for h in BASKET:
        closes = [c for _, c in histories[h.ticker]][-len(nav):]
        ret = (closes[-1] / closes[0] - 1.0) * 100.0
        holdings.append({"ticker": h.ticker, "label": h.label, "weight": h.weight,
                         "start_price": round(closes[0], 2), "end_price": round(closes[-1], 2),
                         "return_pct": round(ret, 2)})

    # the creators who chose to reinvest their payout at the start of the window
    pool = ReinvestmentPool(dates=dates, nav=nav)
    creators = make_global_creators(5000, seed=3)
    reinvesting = [c for i, c in enumerate(creators) if i % 4 == 0]   # ~25% opt in
    for c in reinvesting:
        pool.contribute(c.name, c.owed, at=0)

    nav_return = (nav[-1] / nav[0] - 1.0) * 100.0
    examples = sorted(({"creator": c.display or c.name, "country": c.country,
                        "contributed": pool.contributed(c.name),
                        "stake_value": pool.stake_value(c.name)} for c in reinvesting[:200]),
                      key=lambda e: e["contributed"], reverse=True)[:8]

    data = {
        "as_of": date_labels[-1],
        "holdings": holdings,
        "nav": {"dates": date_labels, "values": nav},
        "nav_return_pct": round(nav_return, 2),
        "pool": {"reinvesting_creators": len(reinvesting),
                 "total_contributed": pool.total_contributed(),
                 "current_value": pool.total_value(),
                 "return_pct": round(nav_return, 2)},
        "examples": examples,
        "note": "Sandbox concept: NAV is priced on real market data, but no securities are "
                "bought. A live version is a regulated securities offering.",
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"as of {data['as_of']}: basket 6mo return {nav_return:+.1f}%")
    for h in holdings:
        print(f"  {h['ticker']:4} {h['label'][:34]:34} {h['return_pct']:+.1f}%  (${h['start_price']} -> ${h['end_price']})")
    print(f"  {len(reinvesting)} creators reinvested ${pool.total_contributed():,.0f} -> now ${pool.total_value():,.0f}")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
