"""The per-creator manager: real earnings windows, recommendations, gated proposals."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.llm import LLMClient  # noqa: E402
from market.manager import CreatorManager  # noqa: E402
from market.marketplace import Account, Listing, Marketplace, Order  # noqa: E402
from marketplace.advance import AdvanceEngine, SafetyFund  # noqa: E402


def _market():
    m = Marketplace()
    for aid in ("s1", "b1", "b2"):
        m.add_account(Account(id=aid, name=aid.upper(), country="US"))
    m.list_item(Listing(id="l1", seller="s1", title="print A", price=100.0, category="prints"))
    m.list_item(Listing(id="l2", seller="s1", title="print B", price=100.0, category="prints"))
    m.place_order(Order(id="o1", buyer="b1", seller="s1", listing="l1", amount=100.0, day=8, status="fulfilled"))
    m.place_order(Order(id="o2", buyer="b2", seller="s1", listing="l2", amount=100.0, day=2, status="fulfilled"))
    bad = m.place_order(Order(id="o3", buyer="b1", seller="s1", listing="l1", amount=100.0, day=9, status="fulfilled"))
    m.mark_return(bad, "returned")
    return m


def test_earnings_windows_net_of_fee():
    mgr = CreatorManager(_market(), "s1", llm=LLMClient(env={}), now_day=10, take_rate=0.10)
    e = mgr.earnings()
    assert e["week"]["net"] == 90.0        # only o1 (day 8) is within 7 days, net of 10% fee
    assert e["month"]["net"] == 180.0      # o1 + o2, returned o3 excluded
    assert e["year"]["net"] == 180.0


def test_recommendations_use_history_and_next_festival():
    mgr = CreatorManager(_market(), "s1", llm=LLMClient(env={}), now_day=10)
    rec = mgr.recommendations()
    assert rec["your_best"] == ["prints"]
    assert rec["next_festival"] == "Valentine's"      # first festival on/after day 10


def test_a_two_week_history_is_too_thin_to_lend_against_profitably():
    # two weeks of sales put PD near 50%; a fee that covers PD x LGD would be above the ceiling,
    # so the manager offers no advance rather than one that loses money on average
    mgr = CreatorManager(_market(), "s1", llm=LLMClient(env={}), now_day=10)
    props = mgr.proposals(SafetyFund(balance=10000.0), AdvanceEngine())
    assert not [p for p in props if p["action"] == "take_advance"]
    assert all(p["needs_approval"] is True for p in props)


def test_a_steady_history_gets_a_gated_advance_priced_to_cover_its_loss():
    from marketplace.advance import ADVANCE_LGD, TARGET_RETURN
    eng = AdvanceEngine()
    o = eng.offer("steady", 1000.0, SafetyFund(10000.0), earnings_history=[200] * 12)
    assert o.eligible and o.pd > 0
    assert o.fee_rate >= o.pd * ADVANCE_LGD + TARGET_RETURN - 1e-9   # the fee pays for its own risk


def test_briefing_is_grounded_without_a_key():
    mgr = CreatorManager(_market(), "s1", llm=LLMClient(env={}), now_day=10)
    text = mgr.briefing(SafetyFund(balance=10000.0), AdvanceEngine())
    assert "180" in text and "approval" in text.lower()
