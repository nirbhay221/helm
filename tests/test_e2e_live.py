"""Live end-to-end test of the two agent journeys, on the real model, through the real API.

Three levels, as agent-graph testing is done in practice:
  - node:       every agent step ran on the model (a fallback anywhere fails the test, with
                the step and the reason it fell back);
  - trajectory: the graph took the expected route through its steps;
  - end state:  the decision is sensible AND the shared account's books moved exactly as the
                decision says (asserted on the API, not on the model's words).

It needs a model key (reads .env) and skips without one. It does not skip on a fallback: a step
that silently fell back to its rules is exactly what this test exists to catch.
"""
from __future__ import annotations

import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except Exception:
    pass

pytestmark = pytest.mark.skipif(not os.environ.get("HELM_LLM_API_KEY"),
                                reason="live end-to-end test needs a model key (HELM_LLM_API_KEY)")

SIGNAL_RISK = "Chargeback spike across the marketplace this week; accounts sharing devices and cards are under review."
SIGNAL_CALM = "Quiet, normal week: no incidents, disputes or flags on any creator."


class _Remote:
    """The same calls against a deployed server (set HELM_E2E_URL), so the hosted demo is tested."""

    def __init__(self, base):
        import requests
        self.base, self.s = base.rstrip("/"), requests.Session()
        self.headers = self.s.headers

    def get(self, p):
        return self.s.get(self.base + p, timeout=240)

    def post(self, p, json=None):
        return self.s.post(self.base + p, json=json or {}, timeout=240)


@pytest.fixture()
def api():
    if os.environ.get("HELM_E2E_URL"):
        c = _Remote(os.environ["HELM_E2E_URL"])
    else:
        from fastapi.testclient import TestClient
        from ui.app import app
        c = TestClient(app)
    c.headers.update({"X-Helm-Session": "e2e-" + uuid.uuid4().hex[:8]})
    c.post("/api/account/reset")
    return c


def _all_model(nodes: dict, expect: set):
    assert expect <= set(nodes), f"missing steps: {expect - set(nodes)}"
    bad = {k: v.get("error") for k, v in nodes.items() if v.get("driver") != "model"}
    assert not bad, f"steps fell back to rules: {bad}"


def _operator(api, signal):
    r = api.post("/api/operator/graph", json={"signal": signal, "debate_rounds": 1})
    assert r.status_code == 200, r.text
    return r.json()


def test_operator_end_to_end_pays_the_clean_and_holds_the_rings(api):
    api.post("/api/market/scan", json={"apply": True})           # the planted rings get suspended
    before = api.get("/api/account").json()
    d = _operator(api, SIGNAL_RISK)
    _all_model(d["nodes"], {"signal_analyst", "risk_analyst", "bull_1", "bear_1", "manager"})
    views = {v["creator"]: v["verdict"] for v in d["risk_views"]}
    assert any(n.endswith("[me]") for n in views) and len(views) >= 4
    suspended = [n for n in views if n.endswith(("[u0000]", "[u0001]", "[u0002]", "[u0003]", "[u0004]", "[u0005]"))]
    assert suspended and all(views[n] == "hold" for n in suspended), views
    dec = d["decision"]
    paid = {p["creator"]: p["amount"] for p in dec.get("paid", [])}
    assert not (set(suspended) & set(paid)), "a suspended creator was paid"
    assert dec["paid_total"] <= dec["safe_release_total"] + 1e-6
    assert d["risk_multiplier"] >= 1.0
    # end state: the payout left the books exactly once, through the creators' ledger
    after = api.get("/api/account").json()
    booked = round(sum(b["amount"] for b in d["booked_to_account"]), 2)
    assert booked == round(dec["paid_total"], 2)
    assert round(before["liabilities"] - after["liabilities"], 2) == booked
    assert round(before["reserves"] - after["reserves"], 2) == booked


def test_operator_is_more_cautious_on_a_risk_signal(api):
    risk = _operator(api, SIGNAL_RISK)
    calm = _operator(api, SIGNAL_CALM)
    _all_model(calm["nodes"], {"risk_analyst", "manager"})
    held = lambda d: sum(v["verdict"] == "hold" for v in d["risk_views"])
    assert held(calm) <= held(risk)


def test_buyer_prefers_a_creator_and_the_sale_pays_them(api):
    start = api.get("/api/account").json()
    d = _buy(api, "I need a trap beat pack for my next video", 60)
    _all_model(d["nodes"], {"understand", "select"})
    c = d["choice"]
    assert c.get("source") == "marketplace" and c.get("seller"), c
    assert d["settlement"]["status"] == "held"
    s = api.post("/api/escrow/settle", json={"escrow_id": d["settlement"]["escrow_id"], "delivered": True}).json()
    assert s["status"] == "released" and s["sale"]["seller"] == c["seller"]
    assert s["sale"]["seller_net"] == round(c["price"] * 0.9, 2)
    assert s["account"]["reserves"] == start["reserves"]
    assert round(start["liabilities"] - s["account"]["liabilities"], 2) == s["sale"]["platform_fee"]


def test_dispute_claws_back_and_builds_evidence(api):
    start = api.get("/api/account").json()
    d = api.post("/api/disputes/simulate", json={}).json()
    assert d["chargeback"]["status"] == "charged_back" and d["seller"] == "me"
    assert round(start["my_earnings"] - d["account"]["my_earnings"], 2) == d["chargeback"]["clawed"]
    assert d["evidence"]["evidences"][0]["notes"]


def _buy(api, need, budget, **kw):
    r = api.post("/api/customer/graph", json={"need": need, "budget": budget, **kw})
    assert r.status_code == 200, r.text
    return r.json()


def test_buyer_end_to_end_buys_the_right_thing_and_holds_it(api):
    start = api.get("/api/account").json()
    d = _buy(api, "I need a good microphone for streaming my videos", 80)
    _all_model(d["nodes"], {"understand", "select"})
    assert d["trace"][:6] == ["understand", "search", "safety", "select", "authorize", "settle"]
    c = d["choice"]
    assert "mic" in (c["title"] or "").lower(), c
    assert 0 < c["price"] <= 80
    assert d["authorization"]["allowed"] is True
    assert d["settlement"]["status"] == "held"
    acct = d["account"]
    assert round(start["my_earnings"] - acct["my_earnings"], 2) == round(c["price"], 2)
    assert [h["escrow_id"] for h in acct["open_holds"]] == [d["settlement"]["escrow_id"]]
    # confirm delivery: captured, the platform pays it out of what it owes, reconciliation clean
    s = api.post("/api/escrow/settle", json={"escrow_id": d["settlement"]["escrow_id"], "delivered": True}).json()
    assert s["status"] == "released" and not s["account"]["open_holds"]
    rec = api.post("/api/reconcile/demo", json={}).json()
    assert rec["clean"] and len(rec["matched"]) == 1


@pytest.mark.parametrize("need,budget,must,must_not", [
    ("I need a laptop", 600, "laptop", ("stand", "lift", "sleeve", "bag", "case")),
    ("a laptop stand for my desk", 60, "stand", ()),
])
def test_buyer_picks_the_thing_not_an_accessory(api, need, budget, must, must_not):
    d = _buy(api, need, budget)
    _all_model(d["nodes"], {"understand", "select"})
    c = d["choice"]
    if c.get("declined"):
        pytest.fail("declined a request the catalog can serve: " + c.get("reason", ""))
    t = (c["title"] or "").lower()
    assert must in t and not any(w in t for w in must_not), c["title"]
    assert c["price"] <= budget


def test_owner_category_limit_binds_the_live_buyer(api):
    start = api.get("/api/account").json()
    d = _buy(api, "I need a good microphone for streaming my videos", 80, categories=["software"])
    assert not (d.get("settlement") or {}).get("status"), "bought outside the owner's categories"
    assert api.get("/api/account").json()["my_earnings"] == start["my_earnings"]
