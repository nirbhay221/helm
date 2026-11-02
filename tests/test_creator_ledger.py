"""The per-creator ledger: hold-until-window, and recoupment on reversal."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marketplace.creator_ledger import CreatorLedger  # noqa: E402


def test_earnings_are_held_until_the_chargeback_window_closes():
    led = CreatorLedger(chargeback_window=4)
    led.accrue("Ava", 100.0, period=0)
    # at period 2 the window has not closed: owed but not yet settled
    assert led.total_unpaid("Ava") == 100.0
    assert led.settled_unpaid("Ava", now=2) == 0.0
    # at period 4 the window has closed: now safe to pay
    assert led.settled_unpaid("Ava", now=4) == 100.0


def test_chargeback_on_unpaid_earnings_just_removes_them():
    led = CreatorLedger(chargeback_window=4)
    led.accrue("Ava", 100.0, period=0)
    debt = led.chargeback("Ava", 40.0, now=1)
    assert debt == 0.0                       # nothing was paid out yet
    assert led.total_unpaid("Ava") == 60.0
    assert led.recoup_due("Ava") == 0.0


def test_chargeback_after_payout_creates_a_recoupable_debt():
    led = CreatorLedger(chargeback_window=4)
    led.accrue("Ben", 100.0, period=0)
    led.pay("Ben", 100.0, now=4)             # released (early or settled)
    debt = led.chargeback("Ben", 30.0, now=6)  # sale reverses after payout
    assert debt == 30.0
    assert led.recoup_due("Ben") == 30.0
    assert led.net_position("Ben") == -30.0  # creator now owes the platform


def test_future_earnings_pay_down_the_debt_before_the_creator_is_paid():
    led = CreatorLedger(chargeback_window=4)
    led.accrue("Ben", 100.0, period=0)
    led.pay("Ben", 100.0, now=4)
    led.chargeback("Ben", 30.0, now=6)
    led.accrue("Ben", 50.0, period=7)        # new earnings
    assert led.recoup_due("Ben") == 0.0      # debt cleared first
    assert led.total_unpaid("Ben") == 20.0   # only the remainder is payable


def test_cannot_pay_more_than_is_owed():
    led = CreatorLedger(chargeback_window=4)
    led.accrue("Cy", 40.0, period=0)
    paid = led.pay("Cy", 999.0, now=4)
    assert paid == 40.0
    assert led.total_unpaid("Cy") == 0.0
