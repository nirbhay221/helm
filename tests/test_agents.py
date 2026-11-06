"""Customer agents drive the marketplace; the bookkeeping stays deterministic.

Keyless (stochastic fallback) so it is offline and reproducible. The live model
path is exercised by scripts/gen_agent_market.py.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.llm import LLMClient  # noqa: E402
from market.agents import AgentMarket  # noqa: E402


def _market():
    return AgentMarket(LLMClient(env={}), n_agents=6, seed=7)   # no key -> stochastic agents


def test_agents_drive_the_market_and_transact():
    mk = _market()
    m = mk.run(5)
    assert len(mk.log) == 5
    assert len(m.orders) >= 1                                   # agents actually traded
    assert all("action" in e for t in mk.log for e in t["events"])


def test_agents_build_memory_and_reflect():
    mk = _market()
    mk.run(4)
    assert all(len(a.memory) > 0 for a in mk.agents)      # each agent recorded what happened
    assert any(a.reflection for a in mk.agents)            # the reflection pass formed lessons


def test_bookkeeping_rules_hold_whatever_the_agent_chose():
    mk = _market()
    mk.run(6)
    for o in mk.m.orders:
        assert o.buyer != o.seller                              # never buy your own listing
        assert o.amount > 0
    # a returned order traces to a real prior purchase by that buyer
    for o in mk.m.orders:
        if o.status == "returned":
            assert any(b.listing == o.listing for b in mk.m.orders_as_buyer(o.buyer))
