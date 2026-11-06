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


def test_proposals_include_a_gated_advance_offer():
    mgr = CreatorManager(_market(), "s1", llm=LLMClient(env={}), now_day=10)
    props = mgr.proposals(SafetyFund(balance=10000.0), AdvanceEngine())
    adv = [p for p in props if p["action"] == "take_advance"]
    assert adv and adv[0]["needs_approval"] is True
    assert adv[0]["pd"] > 0                            # risk-priced from the creator's earnings history
    assert adv[0]["up_to"] <= round(0.8 * 180.0, 2)    # risk-adjusted, never above the unadjusted cap


def test_briefing_is_grounded_without_a_key():
    mgr = CreatorManager(_market(), "s1", llm=LLMClient(env={}), now_day=10)
    text = mgr.briefing(SafetyFund(balance=10000.0), AdvanceEngine())
    assert "180" in text and "approval" in text.lower()
