"""The signal desk reads a free-text signal into a bounded forecast adjustment.

Keyless (no model key -> scripted parser), so it is offline and deterministic.
The live model and self-consistency paths are exercised by scripts/smoke_all.py.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.llm import LLMClient  # noqa: E402
from agent.signals import SignalDesk, _disagreement, _median  # noqa: E402


def test_median_and_disagreement_helpers():
    assert _median([3, 1, 2]) == 2
    assert _median([1, 2, 3, 4]) == 2.5
    assert _disagreement([5, 5, 5]) == 0.0           # unanimous
    assert _disagreement([0, 0, 0]) == 0.0
    assert 0.0 < _disagreement([100, -100, 0]) <= 1.0  # wide spread -> high disagreement


def test_keyless_fallback_parses_a_clear_signal():
    desk = SignalDesk(LLMClient(env={}))             # no key -> scripted parser
    a = desk.interpret("Demand will triple in week 3 for this product.",
                       current_period=0, baseline_demand=1000, horizon=6)
    assert a.source == "fallback"
    assert a.delta_for(3) > 0                         # a positive bump at week 3


def test_vague_signal_yields_no_change():
    desk = SignalDesk(LLMClient(env={}))
    a = desk.interpret("Things were pretty normal this week.",
                       current_period=0, baseline_demand=1000, horizon=6)
    assert a.is_empty()
