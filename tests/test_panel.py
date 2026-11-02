"""The model panel aggregates votes by consensus and trims the bet on disagreement.

Deterministic and keyless: a stub desk returns canned per-model votes, so the
aggregation math is tested without any network. The live panel is exercised by
scripts/demo_panel.py.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.signals import ForecastAdjustment, SignalDesk, _disagreement, _median  # noqa: E402


class _StubDesk(SignalDesk):
    """A desk whose per-model answers are canned (keyed by model id)."""
    def __init__(self, votes: dict[str, dict[int, float]]):
        super().__init__(llm=None, models=list(votes.keys()))
        self._votes = votes

    @property
    def available(self) -> bool:
        return True

    def _interpret_llm(self, signal_text, current_period, baseline_demand, horizon, model=None):
        return ForecastAdjustment(period_deltas=dict(self._votes[model]),
                                  cited_signal="promo week 24", source="model")


def test_median_and_disagreement_helpers():
    assert _median([34, 34, 34]) == 34
    assert _median([5, 34, 34, 34]) == 34         # even count, two middle 34s
    assert _disagreement([34, 34, 34]) == 0.0      # unanimous
    assert _disagreement([0, 0, 0]) == 0.0         # agree on nothing
    assert _disagreement([34, -34]) >= 0.99        # opposite -> maximal


def test_unanimous_panel_acts_in_full():
    desk = _StubDesk({"a": {24: 34.0}, "b": {24: 34.0}, "c": {24: 34.0}})
    adj = desk.interpret("promo week 24", 22, 17.0, 8)
    assert adj.source == "panel"
    assert adj.disagreement == 0.0
    assert adj.confidence == 1.0
    assert adj.period_deltas == {24: 34.0}


def test_one_noisy_model_is_outvoted_and_trims_confidence():
    desk = _StubDesk({"a": {24: 34.0}, "b": {24: 34.0}, "c": {24: 34.0}, "weak": {24: 5.0}})
    adj = desk.interpret("promo week 24", 22, 17.0, 8)
    # median of [5,34,34,34] is 34: the noisy vote does not flip the consensus
    assert adj.disagreement > 0.0
    assert adj.confidence < 1.0
    # the bet is the consensus scaled by confidence, so smaller than 34
    assert 0 < adj.period_deltas[24] < 34.0


def test_incoherent_panel_shrinks_bet_toward_zero():
    desk = _StubDesk({"a": {24: 34.0}, "b": {24: -34.0}, "c": {24: 0.0}})
    adj = desk.interpret("promo week 24", 22, 17.0, 8)
    assert adj.disagreement >= 0.9        # they point opposite ways
    assert adj.confidence <= 0.1
    # median is 0 here, so no bet survives
    assert adj.is_empty()
