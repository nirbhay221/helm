"""The owner's signed limit caps what the agent spends. A purchase the owner makes by hand with Buy now
does not use it up, and a freshly signed limit starts from zero."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import market.delivery as delivery  # noqa: E402
from market.escrow import Escrow  # noqa: E402
from marketplace.account import Account  # noqa: E402


def _held(self, client, ledger):
    self.status, self.authorization_id = "held", "AUTH-" + str(self.amount)
    return {"status": "held", "reason": "ok"}


def _setup(monkeypatch):
    monkeypatch.setattr(Escrow, "fund", _held)
    monkeypatch.setattr(delivery, "deliver_and_inspect", lambda acct, eid: {"delivery": None, "inspection": None})
    a = Account()
    a.sign_mandate(65)
    return a


def test_buy_now_by_hand_does_not_use_up_the_agents_limit(monkeypatch):
    a = _setup(monkeypatch)
    a.hold_purchase("Moody film presets", 29.43, "x", client=None, by_agent=False)
    assert a.mandate_view()["remaining"] == 65
    a.hold_purchase("Botanical art print", 56.15, "x", client=None)
    assert a.mandate_view()["spent"] == 56.15


def test_a_fresh_signature_starts_from_zero_even_with_holds_open(monkeypatch):
    a = _setup(monkeypatch)
    a.hold_purchase("Botanical art print", 56.15, "x", client=None)
    a.sign_mandate(80)
    assert a.mandate_view()["spent"] == 0 and a.mandate_view()["remaining"] == 80


def test_a_dispute_reviews_its_own_parties_not_the_whole_market():
    from marketplace.account import ME
    from marketplace.disputes import apply_dispute, simulated_dispute
    a = Account()
    mine = [o for o in a.market.orders_as_seller(ME) if o.status == "fulfilled"]
    o = max(mine, key=lambda x: x.day)
    apply_dispute(a, simulated_dispute(a, o.id), client=None)
    others = [s for s in a.sellers() if a.frozen(s) and s not in (o.seller, o.buyer)]
    assert others == []                       # the planted rings wait for the operator's scan
    assert a.scan(apply=True)["suspended"]    # and the scan still finds them


def test_trust_rewards_a_long_clean_record_over_a_short_one():
    from market.marketplace import trust_score
    assert trust_score(396, 400) > trust_score(3, 3)        # 400 sales, 1% back beats 3 clean sales
    assert trust_score(90, 100) > trust_score(60, 100)
    assert trust_score(0, 0) == 0


def test_the_buyer_agent_sees_each_sellers_trust():
    a = Account()
    hits = a.search_listings("print")
    assert hits and all(isinstance(h["trust"], int) and 0 <= h["trust"] <= 100 for h in hits)


def test_filler_words_never_match_a_listing():
    a = Account()
    assert a.search_listings("a laptop stand for my desk") == []          # "for" must not hit "Short-form"
    assert a.search_listings("I need a botanical art print")[0]["title"] == "Botanical art print"
