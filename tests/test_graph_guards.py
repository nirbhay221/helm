"""Deterministic guards on the two agent graphs: the owner's mandate binds a hijacked buyer, and
each step reports honestly whether the model or the rules ran it. Hermetic: no keys."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.llm import LLMClient
from market.customer_graph import CustomerGraph
from market.mandates import OwnerKey, issue_intent_mandate


def _buyer(choice_id="p1", label="audio", products=None):
    g = CustomerGraph(llm=LLMClient(env={}), env={})
    cat = [{"id": "p1", "title": "Webcam 4K", "price": 50.0, "merchant": "m", "category": "video"}]

    def ask(system, user, schema, temperature=0.2):
        if schema["name"] == "set_intent":
            return {"query": "microphone", "category": label, "max_price": 80}, "model"
        return {"id": choice_id, "reason": "best fit"}, "model"
    g._ask = ask
    g.search = lambda st: (st["trace"].append("search"), st.update(products=list(products or cat),
                                                                       backend="test"))[1] or st
    g.app = g._build()
    return g


def test_mandate_is_signed_before_the_agents_run():
    st = _buyer().run("a microphone", 80)
    assert st["mandate"]["payload"]["type"] == "IntentMandate"
    assert st["mandate"]["public_key"] == st["owner_key"]


def test_agent_cannot_relabel_a_product_past_the_owners_categories():
    # the model calls it "audio", but the listing is a video product; the owner allowed audio only
    st = _buyer(label="audio").run("a microphone", 80, categories=["audio"])
    assert st["choice"]["category"] == "video"
    assert st["authorization"]["allowed"] is False
    assert "settlement" not in st


def test_allowed_category_is_bought():
    st = _buyer().run("a webcam", 80, categories=["video"])
    assert st["authorization"]["allowed"] is True and st["settlement"]


def test_mandate_signed_by_someone_else_is_refused():
    g = _buyer()
    attacker = OwnerKey()
    forged = issue_intent_mandate(attacker, owner="buyer", max_total=1e6, max_per_item=1e6)
    st = g.app.invoke({"need": "x", "budget": 80, "mandate": forged, "owner_key": OwnerKey().public_pem()})
    assert st["authorization"]["allowed"] is False and "rejected" in st["authorization"]["reason"]


def test_buyer_nodes_record_who_ran_each_step():
    st = _buyer().run("a webcam", 80)
    assert st["nodes"]["understand"]["driver"] == "model"
    assert st["nodes"]["select"]["driver"] == "model"
    off = CustomerGraph(llm=LLMClient(env={}), env={}).run("a ring light", 60)
    assert off["nodes"]["understand"] == {"driver": "fallback", "error": "no model key"}


def test_model_inventing_a_product_id_is_reported_as_a_fallback():
    st = _buyer(choice_id="does-not-exist").run("a webcam", 80)
    assert st["nodes"]["select"]["driver"] == "fallback"
    assert "not in the catalog" in st["nodes"]["select"]["error"]


def test_operator_partial_verdicts_are_not_called_model():
    from marketplace.account import Account
    from ui.app import _build_operator_graph
    graph, _, ids = _build_operator_graph(1, Account())
    graph.llm = LLMClient(env={"HELM_LLM_API_KEY": "x", "HELM_LLM_BASE_URL": "http://invalid"})
    names = list(ids)
    forgotten = names[-1]

    def ask(system, user, schema, temperature=0.2):
        graph._last_error = None
        if schema["name"] == "classify_creators":     # the model forgets the last creator
            return {"verdicts": [{"creator": n, "verdict": "pay", "reason": "clean"} for n in names[:-1]]}, "model"
        if schema["name"] == "argue":
            return {"argument": "x", "pushes_multiplier": 1.1}, "model"
        return {"risk_multiplier": 1.1, "allocations": [{"creator": names[0], "amount": 100}]}, "model"
    graph._ask = ask
    st = graph.step("normal week")
    assert st["nodes"]["risk_analyst"]["driver"] == "fallback"
    assert forgotten in st["nodes"]["risk_analyst"]["error"]
    assert st["nodes"]["manager"]["driver"] == "model"
    assert st["driver"] == "fallback"
    assert {"bull_1", "bear_1"} <= set(st["nodes"])
