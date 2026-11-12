"""An AI customer whose model call fails sits the turn out and says so; it never acts at random."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market.agents import AgentMarket  # noqa: E402


class _Down:
    available = True
    last_model = None

    def chat(self, **kw):
        raise RuntimeError("rate limited")


class _NoKey:
    available = False


def test_a_failed_model_call_holds_and_is_labelled():
    mk = AgentMarket(llm=_Down(), n_agents=3, seed=1)
    events = mk.tick()
    assert events and all(e["action"] == "hold" and e["driver"] == "error" for e in events)


def test_no_key_runs_the_labelled_simulation():
    mk = AgentMarket(llm=_NoKey(), n_agents=3, seed=1)
    events = mk.tick()
    assert all(e["driver"] == "sim" for e in events)
