"""Predictive P&L: expected loss is PD x LGD x EAD, risk pricing covers the loss, and
the forward P&L carries a band, a CECL provision, and a RAROC."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marketplace.pnl import (  # noqa: E402
    LoanExposure, PlatformPnL, expected_loss, risk_adjusted_price,
)


def test_expected_loss_is_pd_lgd_ead():
    assert expected_loss(0.2, 0.5, 1000) == 100.0
    assert expected_loss(0.0, 0.5, 1000) == 0.0


def test_risk_pricing_covers_expected_loss_and_has_a_floor():
    cheap = risk_adjusted_price(0.02, 0.55)       # low PD
    pricey = risk_adjusted_price(0.40, 0.55)      # high PD
    assert pricey > cheap                          # riskier pays more
    assert risk_adjusted_price(0.0, 0.55) >= 0.02  # never below the floor


def test_forward_pnl_has_band_provision_and_raroc():
    gmv = [{"mean": 10000, "low": 8000, "high": 12000},
           {"mean": 11000, "low": 8500, "high": 13500}]
    book = [LoanExposure("ava", pd=0.2, ead=1000), LoanExposure("ben", pd=0.1, ead=500)]
    out = PlatformPnL().forecast(gmv, book, fund_balance=500.0)
    # expected loss = advances + chargebacks
    assert out["expected_loss"]["advances"] == round(0.2 * 0.55 * 1000 + 0.1 * 0.55 * 500, 2)
    assert out["expected_loss"]["total"] == round(out["expected_loss"]["advances"]
                                                  + out["expected_loss"]["chargebacks"], 2)
    # profit carries a band ordered low <= mean <= high
    p = out["risk_adjusted_profit"]
    assert p["low"] <= p["mean"] <= p["high"]
    # provision is the coverage multiple of expected loss
    assert out["provision_needed"] == round(out["expected_loss"]["total"] * 1.2, 2)
    assert out["raroc"] is not None
    assert out["book_exposure"] == 1500.0


def test_fund_coverage_flag():
    gmv = [{"mean": 1000, "low": 1000, "high": 1000}]
    book = [LoanExposure("x", pd=0.5, ead=1000)]      # EL = 275
    low_fund = PlatformPnL().forecast(gmv, book, fund_balance=100.0)
    assert low_fund["fund_covers_provision"] is False
    high_fund = PlatformPnL().forecast(gmv, book, fund_balance=100000.0)
    assert high_fund["fund_covers_provision"] is True
