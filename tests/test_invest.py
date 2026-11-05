"""Real paper investing: fractional buys at live price, marked to market."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marketplace.invest import Business, PaperBroker, Portfolio  # noqa: E402
from marketplace.reinvest import BASKET  # noqa: E402


def test_invest_buys_fractional_units_and_marks_to_market():
    prices = {"SPY": 100.0, "VNQ": 50.0, "MCD": 200.0}
    broker = PaperBroker(price_fn=lambda t: prices[t], use_alpaca=False)
    pf = Portfolio(broker)
    pf.invest(1000.0)                                   # 50/30/20 across the basket
    assert abs(pf.cost_basis() - 1000.0) < 1e-6
    assert abs(pf.market_value() - 1000.0) < 1e-6      # value == cost at entry prices
    # SPY sleeve was 500 at 100 -> 5 units
    assert abs(pf.positions["SPY"].units - 5.0) < 1e-6
    # market moves up 10% on SPY -> portfolio gains
    prices["SPY"] = 110.0
    assert pf.market_value() > 1000.0
    assert pf.return_pct() > 0.0


def test_broker_backend_is_paper_without_keys():
    broker = PaperBroker(price_fn=lambda t: 1.0, env={})
    assert broker.backend == "paper-live-price"
    fill = broker.buy("SPY", 100.0)
    assert fill["units"] == 100.0 and fill["routed_to_alpaca"] is False


def test_business_shares_are_prorata_and_capped_at_target():
    b = Business("Lagos Coffee", "restaurant", target=1000.0, monthly_return=0.02)
    assert b.back("Ava", 600.0) == 600.0
    assert b.back("Ben", 600.0) == 400.0               # capped at the remaining target
    assert abs(b.share_of("Ava") - 0.6) < 1e-6
    assert b.value_for("Ava", months=1) == round(600.0 * 1.02, 2)
