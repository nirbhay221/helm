"""The tax statement reports the right figures under the US and EU regimes."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market.marketplace import Account, Listing, Marketplace, Order  # noqa: E402
from marketplace.tax import build_statement  # noqa: E402


def _market_with_sales(seller_country: str, n: int, price: float):
    m = Marketplace()
    m.add_account(Account(id="s1", name="S", country=seller_country))
    m.add_account(Account(id="b1", name="B", country="US"))
    m.list_item(Listing(id="l1", seller="s1", title="x", price=price, category="prints"))
    for i in range(n):
        m.place_order(Order(id=f"o{i}", buyer="b1", seller="s1", listing="l1",
                            amount=price, day=i % 100, status="fulfilled"))
    return m


def test_us_1099k_is_gross_and_below_threshold_is_not_reportable():
    st = build_statement(_market_with_sales("US", 10, 100.0), "s1", "US", fee_rate=0.1)
    assert st.regime["form"] == "US 1099-K"
    assert st.regime["box_1a_gross"] == 1000.0 and st.regime["transactions"] == 10
    assert st.regime["reportable_federally"] is False       # under $20k and 200 tx
    assert st.net == 900.0                                   # gross minus 10% fee


def test_us_1099k_over_threshold_is_reportable():
    st = build_statement(_market_with_sales("US", 250, 200.0), "s1", "US")
    assert st.regime["reportable_federally"] is True         # $50k and 250 tx


def test_dac7_de_minimis_exempts_a_small_eu_seller():
    small = build_statement(_market_with_sales("DE", 5, 50.0), "s1", "DE")
    assert small.regime["form"] == "DAC7"
    assert small.regime["de_minimis_exempt"] is True         # under 30 activities and under EUR 2000
    big = build_statement(_market_with_sales("DE", 40, 100.0), "s1", "DE")
    assert big.regime["de_minimis_exempt"] is False
