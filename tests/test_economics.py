"""Platform cuts and float feed the safety fund and the platform's revenue."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marketplace.advance import SafetyFund  # noqa: E402
from marketplace.economics import PlatformEconomics, UnitEconomics  # noqa: E402


def test_payout_fee_splits_to_fund_and_revenue():
    fund = SafetyFund(balance=0.0)
    econ = PlatformEconomics(fund, payout_fee_rate=0.02, fund_share=0.5)
    out = econ.on_payout(1000.0)                 # 2% fee = 20, split 50/50
    assert out["cut"] == 20.0
    assert out["to_fund"] == 10.0 and fund.balance == 10.0
    assert out["to_revenue"] == 10.0 and econ.revenue == 10.0


def test_float_yield_accrues_over_time():
    fund = SafetyFund(balance=0.0)
    econ = PlatformEconomics(fund, float_apr=0.04, fund_share=0.5)
    out = econ.on_float(10000.0, days=365)       # a full year at 4% = 400
    assert out["cut"] == 400.0 and fund.balance == 200.0


def test_advance_fee_backs_the_fund_that_took_the_risk():
    fund = SafetyFund(balance=100.0)
    econ = PlatformEconomics(fund, fund_share=1.0)
    econ.on_advance_fee(48.0)                     # all of it to the fund
    assert fund.balance == 148.0 and econ.revenue == 0.0


def test_unit_economics_arpu_ltv_and_viability():
    ue = UnitEconomics(interchange_rate=0.015, float_apr=0.04, cost_of_funds=0.01,
                       payout_fee_rate=0.02, advance_fee_rate=0.06, cac_per_creator=20.0,
                       churn_monthly=0.03, gross_margin=0.8)
    ue.add_creators(100)
    ue.record_card_spend(50000.0)                 # interchange 1.5% = 750
    ue.record_float(200000.0)                     # monthly NIM = 200000 * 0.03 / 12 = 500
    ue.record_payouts(100000.0)                   # 2% = 2000
    ue.record_advances(10000.0)                   # 6% = 600
    assert ue.monthly_revenue() == 3850.0
    assert ue.arpu() == 38.5
    assert ue.lifetime_months() == 33.3
    assert ue.ltv() == round(38.5 * 33.3 * 0.8, 2)
    assert ue.ltv_cac() == round(ue.ltv() / 20.0, 2)
    assert ue.viable() is True                    # LTV:CAC well above 3x
    assert abs(sum(ue.revenue_mix().values()) - 1.0) < 0.01
