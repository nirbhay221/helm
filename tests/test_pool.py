"""Pools are safe and fair: signed mandates gate contributions, ownership is
pro-rata, and the bulk-discount saving splits by an efficient Shapley rule."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market.mandates import OwnerKey, issue_intent_mandate  # noqa: E402
from market.pool import (  # noqa: E402
    GroupBuy, InvestmentPool, discount_rate, shapley_discount_split,
)
from marketplace.invest import PaperBroker  # noqa: E402


def _broker():
    # fixed price, no network, no Alpaca: a clean unit test of the mechanics.
    return PaperBroker(price_fn=lambda t: 100.0, use_alpaca=False)


def _signed(owner: str, budget: float, category: str = "stocks"):
    key = OwnerKey()
    return issue_intent_mandate(key, owner, max_total=budget, max_per_item=budget,
                                allowed_categories=[category])


# --- investment pool --------------------------------------------------------

def test_investment_pool_splits_units_pro_rata():
    pool = InvestmentPool(asset="SPY")
    pool.join("ann", 300.0, _signed("ann", 300.0))
    pool.join("ben", 100.0, _signed("ben", 100.0))
    out = pool.execute(_broker())
    assert out["funded_total"] == 400.0
    assert abs(out["total_units"] - 4.0) < 1e-6          # $400 / $100
    shares = {a["member"]: a["share"] for a in out["allocations"]}
    assert abs(shares["ann"] - 0.75) < 1e-6 and abs(shares["ben"] - 0.25) < 1e-6
    assert abs(sum(a["share"] for a in out["allocations"]) - 1.0) < 1e-6


def test_investment_pool_caps_to_the_signed_budget():
    pool = InvestmentPool(asset="SPY")
    pool.join("cara", 500.0, _signed("cara", 200.0))     # asked 500, signed only 200
    out = pool.execute(_broker())
    assert out["funded_total"] == 200.0
    assert out["allocations"][0]["funded"] == 200.0
    assert "capped" in out["allocations"][0]["reason"]


def test_investment_pool_rejects_a_tampered_mandate():
    pool = InvestmentPool(asset="SPY")
    cred = _signed("dan", 100.0)
    cred["payload"]["max_total"] = 100000.0              # forge a bigger budget, do not re-sign
    pool.join("dan", 100000.0, cred)
    out = pool.execute(_broker())
    assert out["funded_total"] == 0.0                    # signature no longer matches -> excluded
    assert out["allocations"][0]["ok"] is False


def test_investment_pool_blocks_a_category_the_owner_did_not_allow():
    pool = InvestmentPool(asset="SPY", category="stocks")
    cred = _signed("eve", 300.0, category="property")    # only allowed property, pool is stocks
    pool.join("eve", 300.0, cred)
    out = pool.execute(_broker())
    assert out["funded_total"] == 0.0


# --- group buy --------------------------------------------------------------

def test_discount_rate_is_monotone_in_quantity():
    assert discount_rate(1) == 0.0
    assert discount_rate(3) >= discount_rate(2)
    assert discount_rate(10) >= discount_rate(5) >= discount_rate(3)


def test_group_buy_unlocks_a_tier_and_saves_money():
    gb = GroupBuy(item="preset pack", unit_price=20.0, category="goods")
    for who in ("a", "b", "c", "d", "e"):               # 5 units -> clears the 10% tier
        gb.join(who, 1.0, _signed(who, 20.0, category="goods"))
    out = gb.allocate()
    assert out["pooled_qty"] == 5.0
    assert out["discount_rate"] == 0.10
    assert out["total_saved"] > 0.0
    assert out["total_paid"] < out["total_list"]


def test_group_buy_shapley_split_is_efficient():
    demands = {"a": 2.0, "b": 2.0, "c": 1.0}             # 5 units total
    split = shapley_discount_split(demands, unit_price=20.0)
    total_saving = 5 * 20.0 * discount_rate(5)
    assert abs(sum(split.values()) - total_saving) < 0.05   # shares sum to the whole saving
    assert all(v >= 0 for v in split.values())
    assert split["a"] >= split["c"]                      # a larger demand earns at least as much


def test_group_buy_excludes_an_unverified_member_from_the_tier():
    gb = GroupBuy(item="preset pack", unit_price=20.0, category="goods")
    gb.join("a", 2.0, _signed("a", 40.0, category="goods"))
    gb.join("b", 2.0, _signed("b", 40.0, category="goods"))
    bad = _signed("c", 40.0, category="goods")
    bad["payload"]["max_total"] = 999.0                  # tamper -> verify fails
    gb.join("c", 2.0, bad)
    out = gb.allocate()
    assert out["pooled_qty"] == 4.0                      # c dropped, only a+b count
