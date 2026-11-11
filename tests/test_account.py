"""One account behind every capability: actions in one tool move the books the others read.

Hermetic: demo PayPal, no model key."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DEMO_MODE", "1")

from fastapi.testclient import TestClient

from agent.llm import LLMClient
from agent.policy import PolicyDesk
from agent.signals import ForecastAdjustment, _why
from market.customer_graph import CustomerGraph
from marketplace.account import ME, NOW_DAY, AccountStore
from paypal import PayPalClient
from ui.app import app

HIST = [900, 1000, 1100, 950, 1050, 1000]


def _client(sid):
    c = TestClient(app)
    c.headers.update({"X-Helm-Session": sid})
    c.post("/api/account/reset")
    return c


def _earned(c):
    return c.get("/api/account").json()["my_earnings"]


def test_advance_moves_the_fund_the_proof_and_the_pnl():
    c = _client("t-adv")
    start = c.get("/api/account").json()
    offer = c.post("/api/advance", json={"creator": "you", "proven_earnings": 3000, "history": HIST}).json()
    assert offer["offer"] <= offer["max_amount"] and offer["offer"] > 0
    took = c.post("/api/advance", json={"creator": "you", "proven_earnings": 3000, "history": HIST,
                                        "take": True}).json()
    assert took["taken"]["status"] == "advanced"
    after = took["account"]
    assert after["reserves"] == round(start["reserves"] - took["taken"]["amount"], 2)
    assert after["margin"] < start["margin"]
    pnl = c.post("/api/pnl", json={}).json()
    assert pnl["book_source"] == "your account's advance book"
    assert pnl["book"][0]["creator"] == "you"
    zk = c.post("/api/reserves/prove", json={}).json()
    assert zk["from_account"] and zk["liabilities_bound"] and zk["solvent"]


def test_cannot_take_more_than_the_safe_offer():
    c = _client("t-over")
    r = c.post("/api/advance", json={"creator": "you", "proven_earnings": 3000, "history": HIST,
                                     "take": True, "amount": 1e6}).json()
    assert r["taken"]["status"] == "rejected"
    assert r["account"]["advances_outstanding"] == 0


def test_purchase_holds_until_delivery_then_captures_and_reconciles():
    c = _client("t-buy")
    start = _earned(c)
    r = c.post("/api/shop/buy", json={"title": "Lamp", "price": 80, "merchant": "m@example.com",
                                      "budget": 200}).json()
    assert r["authorized"] and r["account"]["my_earnings"] == round(start - 80, 2)
    assert r["account"]["open_holds"][0]["escrow_id"] == r["escrow_id"]
    s = c.post("/api/escrow/settle", json={"escrow_id": r["escrow_id"], "delivered": True}).json()
    assert s["status"] == "released" and not s["account"]["open_holds"]
    rec = c.post("/api/reconcile/demo", json={}).json()
    assert rec["clean"] and len(rec["matched"]) == 1


def test_failed_delivery_returns_the_earnings():
    c = _client("t-void")
    start = _earned(c)
    r = c.post("/api/shop/buy", json={"title": "Chair", "price": 300, "merchant": "m@example.com",
                                      "budget": 400}).json()
    s = c.post("/api/escrow/settle", json={"escrow_id": r["escrow_id"], "delivered": False}).json()
    assert s["status"] == "refunded" and s["account"]["my_earnings"] == start


def test_cannot_spend_more_than_earned():
    c = _client("t-broke")
    r = c.post("/api/shop/buy", json={"title": "TV", "price": _earned(c) + 1, "merchant": "m",
                                      "budget": 99999}).json()
    assert r["authorized"] is False and not r["account"]["open_holds"]


def test_tamper_demo_never_edits_the_real_chain():
    c = _client("t-chain")
    c.post("/api/shop/buy", json={"title": "Lamp", "price": 10, "merchant": "m", "budget": 50})
    t = c.post("/api/receipts/demo", json={"tamper": True}).json()
    assert t["verification"]["intact"] is False
    assert c.get("/api/account").json()["chain_intact"] is True


def test_visitors_are_isolated():
    a, b = _client("t-a"), _client("t-b")
    start = _earned(b)
    a.post("/api/shop/buy", json={"title": "Lamp", "price": 50, "merchant": "m", "budget": 100})
    assert _earned(b) == start


def test_payout_to_a_borrower_repays_the_advance():
    acct = AccountStore().get("x")
    acct.take_advance(ME, 500, 3000, HIST)
    owed = acct.engine.loans[ME].outstanding
    fund_before = acct.reserves()
    acct.record_payouts([{"creator": ME, "amount": 400}])
    assert acct.engine.loans[ME].outstanding == round(owed - 100, 2)      # 25% withheld
    assert acct.reserves() == round(fund_before - 400 + 100, 2)


def test_buyer_declines_when_nothing_fits():
    g = CustomerGraph(llm=LLMClient(env={}), env={})
    g._ask = lambda *a, **k: ({"id": "none", "reason": "only a laptop stand was found, not a laptop"}, "model")
    st = {"trace": [], "budget": 500, "need": "a laptop",
          "products": [{"id": "p1", "title": "Laptop Lift stand", "price": 40, "merchant": "m"}]}
    out = g.select(st)
    assert out["choice"]["declined"] and not out["choice"]["id"]


def test_buyer_spend_check_blocks_settlement():
    calls = []
    g = CustomerGraph(llm=LLMClient(env={}), env={}, spend_check=lambda p: (False, "not enough earned"),
                      hold=lambda *a: calls.append(a))
    st = g.run("a ring light for my studio", 60)
    assert not st.get("authorization", {}).get("allowed") and not calls


def test_policy_reading_that_claims_an_exclusion_is_flagged():
    d = PolicyDesk(llm=LLMClient(env={}))._assemble(
        {"speed": 1, "tax": 1, "risk": 1, "fx": 1, "exclude_countries": [],
         "reading": "Exclude all countries from payouts."}, source="model",
        policy_text="exclude all countries")
    assert any("none were compiled" in v for v in d.violations)
    assert "pay no one in" not in d.compiled


def test_policy_readback_is_written_from_the_numbers():
    d = PolicyDesk(llm=LLMClient(env={}))._assemble(
        {"speed": 1, "tax": 1, "risk": 1, "fx": 1, "max_fraction_per_creator": 0.2,
         "exclude_countries": ["NG"]}, source="model")
    assert "20%" in d.compiled and "NG" in d.compiled


def test_signal_rationale_keeps_the_models_reasoning():
    v = [ForecastAdjustment(rationale="a hurricane raises demand for supplies next week"),
         ForecastAdjustment(rationale="")]
    s = _why(v, "agreement across 2 reads 80%")
    assert s.startswith("a hurricane raises demand") and "80%" in s


def test_books_are_computed_from_marketplace_sales():
    acct = AccountStore().get("books")
    led = acct.cledger
    assert acct.liabilities() == round(sum(led.total_unpaid(x) for x in acct.sellers()), 2)
    assert acct.my_earnings == led.total_unpaid(ME) > 0
    assert 0 < led.settled_unpaid(ME, NOW_DAY) < led.total_unpaid(ME)      # some still at chargeback risk
    assert acct.reserves() > acct.liabilities()                             # the fund starts solvent


def test_buying_a_creator_listing_pays_that_creator_and_keeps_the_take():
    c = _client("t-mkt")
    p = next(x for x in c.post("/api/shop/search", json={"query": "beat", "budget": 60}).json()["products"]
             if x.get("source") == "marketplace")
    before = c.get("/api/account").json()
    r = c.post("/api/shop/buy", json={"title": p["title"], "price": p["price"], "merchant": p["merchant"],
                                      "budget": 60, "category": p["category"], "listing": p["listing"]}).json()
    s = c.post("/api/escrow/settle", json={"escrow_id": r["escrow_id"], "delivered": True}).json()
    sale = s["sale"]
    assert sale["seller"] == p["seller"] and sale["seller_net"] == round(p["price"] * 0.9, 2)
    after = s["account"]
    assert after["reserves"] == before["reserves"]                          # money stayed on the platform
    assert after["liabilities"] == round(before["liabilities"] - sale["platform_fee"], 2)


def test_mandate_running_total_blocks_repeat_buys():
    c = _client("t-mand")
    ok = c.post("/api/shop/buy", json={"title": "A", "price": 40, "merchant": "m", "budget": 50}).json()
    assert ok["authorized"]
    no = c.post("/api/shop/buy", json={"title": "B", "price": 40, "merchant": "m", "budget": 50}).json()
    assert no["authorized"] is False and "already spent" in no["reason"]


def test_scan_suspends_rings_and_freezes_their_payouts():
    acct = AccountStore().get("scan")
    r = acct.scan()
    assert {"u0000", "u0003"} <= set(r["suspended"]) and r["frozen_earnings"] > 0
    victim = r["suspended"][0]
    owed = acct.cledger.total_unpaid(victim)
    assert acct.record_payouts([{"creator": victim, "amount": 50}]) == []
    assert acct.cledger.total_unpaid(victim) == owed
    assert all(p["seller"] not in r["suspended"] for p in acct.search_listings("", limit=50))


def test_dispute_claws_back_from_the_seller_once():
    from marketplace.disputes import apply_dispute, simulated_dispute
    acct = AccountStore().get("disp")
    o = max((x for x in acct.market.orders_as_seller(ME) if x.status == "fulfilled"), key=lambda x: x.day)
    start = acct.my_earnings
    ev = simulated_dispute(acct, o.id)
    out = apply_dispute(acct, ev)
    assert out["chargeback"]["status"] == "charged_back"
    assert acct.my_earnings == round(start - o.amount * 0.9, 2)
    assert out["evidence"]["evidences"][0]["notes"] and out["evidence_submitted"] is False
    assert apply_dispute(acct, ev)["status"] == "duplicate"
    won = {**ev, "event_type": "CUSTOMER.DISPUTE.RESOLVED",
           "resource": {**ev["resource"], "dispute_outcome": {"outcome_code": "RESOLVED_SELLER_FAVOUR"}}}
    assert apply_dispute(acct, won)["credited_back"] == round(o.amount * 0.9, 2)
    assert acct.my_earnings == start


def test_operator_cohort_comes_from_the_marketplace():
    from ui.app import _build_operator_graph
    acct = AccountStore().get("op")
    acct.scan()
    graph, _, ids = _build_operator_graph(1, acct)
    assert ME in ids.values() and len(ids) >= 4
    tools = graph.tools if hasattr(graph, "tools") else graph.t
    frozen = [n for n, x in ids.items() if acct.frozen(x)]
    assert frozen and all(tools.led.total_unpaid(n) == 0 for n in frozen)
