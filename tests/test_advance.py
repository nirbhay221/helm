"""Advances are capped by the safety fund and by earnings, gated, and self-repaying."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marketplace.advance import AdvanceEngine, SafetyFund  # noqa: E402


def test_offer_is_capped_by_the_smaller_of_earnings_and_fund_concentration():
    fund = SafetyFund(balance=10000.0)
    eng = AdvanceEngine(advance_rate=0.8, concentration=0.2)
    # earnings small -> earnings binds: 0.8 * 1000 = 800 < 0.2 * 10000 = 2000
    o1 = eng.offer("Ava", proven_earnings=1000.0, fund=fund)
    assert o1.max_amount == 800.0 and o1.binding_cap == "earnings"
    # earnings large -> fund concentration binds: 0.2 * 10000 = 2000 < 0.8 * 5000 = 4000
    o2 = eng.offer("Ben", proven_earnings=5000.0, fund=fund)
    assert o2.max_amount == 2000.0 and o2.binding_cap == "fund-concentration"


def test_advance_needs_human_approval_and_cannot_exceed_cap():
    fund = SafetyFund(balance=10000.0)
    eng = AdvanceEngine()
    held = eng.take("Ava", 800.0, proven_earnings=1000.0, fund=fund, approved=False)
    assert held["status"] == "needs_approval"          # the gate
    over = eng.take("Ava", 5000.0, proven_earnings=1000.0, fund=fund, approved=True)
    assert over["status"] == "rejected"                # above the safe cap
    ok = eng.take("Ava", 800.0, proven_earnings=1000.0, fund=fund, approved=True)
    assert ok["status"] == "advanced" and ok["fee"] == round(800.0 * 0.06, 2)
    assert fund.balance == 10000.0 - 800.0             # the fund fronted the cash


def test_concentration_cap_protects_the_fund_from_one_borrower():
    # a tiny fund can never expose more than 20% to one creator, however much they earned
    fund = SafetyFund(balance=1000.0)
    eng = AdvanceEngine(concentration=0.2)
    o = eng.offer("Whale", proven_earnings=1_000_000.0, fund=fund)
    assert o.max_amount == 200.0 and o.binding_cap == "fund-concentration"


def test_fund_coverage_caps_the_whole_book_not_just_one_borrower():
    from marketplace.advance import Advance
    fund = SafetyFund(balance=120.0)
    eng = AdvanceEngine(loss_rate=0.1, coverage_ratio=1.2)
    assert eng.portfolio_capacity(fund) == 1000.0        # 120 / (1.2 * 0.1)
    eng.loans["x"] = Advance("x", 1000.0, 0.0, 1000.0, 0.25)   # book already full
    assert eng.portfolio_capacity(fund) == 0.0
    o = eng.offer("new", proven_earnings=1000.0, fund=fund)
    assert o.max_amount == 0.0                            # the fund can back no more


def test_risk_pricing_from_earnings_history():
    fund = SafetyFund(balance=100000.0)
    eng = AdvanceEngine()
    steady = eng.offer("Steady", 1000.0, fund, earnings_history=[100, 100, 100, 100, 100, 100])
    volatile = eng.offer("Volatile", 1000.0, fund, earnings_history=[10, 300, 0, 250, 5, 400])
    assert steady.pd < volatile.pd                     # volatility raises default risk
    assert steady.max_amount > volatile.max_amount     # the safer creator is lent more
    assert steady.fee_rate < volatile.fee_rate         # and pays a lower fee


def test_advance_repays_itself_from_future_payouts():
    fund = SafetyFund(balance=10000.0)
    eng = AdvanceEngine(fee_rate=0.06, repay_pct=0.25)
    eng.take("Ava", 800.0, proven_earnings=1000.0, fund=fund, approved=True)
    outstanding = 800.0 * 1.06
    r = eng.repay_from_payout("Ava", 1000.0, fund)     # withhold 25% of the payout
    assert r["withheld"] == 250.0
    assert r["net"] == 750.0
    assert abs(r["outstanding"] - (outstanding - 250.0)) < 1e-6
