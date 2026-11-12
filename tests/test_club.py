"""The investment club: agents pick on their own, then revise after seeing each other; the manager
merges; code caps any company at 35% and each member at their signed limit; the rest stays cash."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market.club import COMMUNITY, InvestmentClub  # noqa: E402


class _Llm:
    available = True
    last_model = model = "test-model"

    def __init__(self, manager_weights):
        self.mw, self.seen = manager_weights, []

    def chat(self, messages, tools, tool_choice, **kw):
        name = tool_choice["function"]["name"]
        self.seen.append((name, messages[0]["content"][:40], json.loads(messages[1]["content"])))
        if name == "pick":
            me = "You's" in messages[0]["content"]
            args = {"reason": "COST is up 14.5% in 3 months", "weights": [{"ticker": "COST", "weight": 0.6},
                                                                     {"ticker": "KO", "weight": 0.4}], "changed": False,
                    "refuses": ["XOM"] if me else []}
        elif name == "club_portfolio":
            args = {"reason": "merged", "weights": [{"ticker": t, "weight": w} for t, w in self.mw.items()]}
        else:
            args = {"lessons": []}
        return {"tool_calls": [{"function": {"arguments": json.dumps(args)}}]}


class _Broker:
    backend = "test"

    def buy(self, t, notional):
        return {"ticker": t, "notional": notional, "price": 100.0, "units": notional / 100.0, "routed_to_alpaca": False}


def _fetch():
    return ({"snapshots": [{"ticker": "COST", "price": 100.0, "return_3m_pct": 14.5, "volatility_pct": 20}],
             "news": [{"headline": "Costco sales rise", "symbols": ["COST"]}]}, [{"tool": "market_snapshot"}])


def _club(mw, me=200.0):
    members = [{"name": "You", "amount": me, "note": "grow, don't gamble", "available": 150.0}] + [dict(m) for m in COMMUNITY]
    llm = _Llm(mw)
    return InvestmentClub(members, llm=llm, broker=_Broker(), memory={}, mcp_fetch=_fetch), llm


def test_agents_pick_alone_then_see_each_other_then_code_caps_the_manager():
    club, llm = _club({"COST": 0.7, "KO": 0.3})
    st = club.run()
    picks = [s for s in llm.seen if s[0] == "pick"]
    assert len(picks) == 8                                           # 4 agents x 2 rounds
    assert all("other_agents_round_1" not in s[2] for s in picks[:4])     # round 1: alone
    assert all(len(s[2]["other_agents_round_1"]) == 3 for s in picks[4:])  # round 2: sees the other three
    d = st["disposed"]
    assert d["weights"]["COST"] == 0.35 and any("COST cut from 70%" in c for c in d["cuts"])
    assert abs(d["cash_share"] - 0.35) < 1e-6                        # what the cap cut stays cash
    you = next(m for m in d["members"] if m["member"] == "You")
    assert you["funded"] == 150.0                                    # capped to earnings available


def test_a_company_off_the_list_is_dropped_and_memory_carries_to_next_round():
    club, _ = _club({"TSLA": 0.5, "KO": 0.5})
    st = club.run()
    assert "TSLA" not in st["disposed"]["weights"]
    assert club.memory["rounds"] == 1 and "KO" in club.memory["positions"]


def test_every_member_node_streams_to_the_control_room():
    from agent import tap
    evs = []
    toks = tap.attach(evs.append)
    try:
        _club({"KO": 0.3, "COST": 0.3, "MCD": 0.4})[0].run()
    finally:
        tap.detach(toks)
    ends = [e["node"] for e in evs if e["kind"] == "node_end" and e.get("graph") == "club"]
    assert ends.count("member_priya") == 2 and "club_manager" in ends and "club_execute" in ends


def test_a_member_who_refused_a_company_puts_none_of_their_money_in_it():
    club, _ = _club({"COST": 0.3, "KO": 0.3, "XOM": 0.4})
    st = club.run()
    you = next(s for s in st["execution"]["shares"] if s["member"] == "You")
    assert "XOM" not in you["holdings"] and you["refused"] == ["XOM"]
    priya = next(s for s in st["execution"]["shares"] if s["member"] == "Priya")
    assert "XOM" in priya["holdings"]                       # the others still get what the club chose
    assert any("none of You's money goes to XOM" in c for c in st["disposed"]["cuts"])
