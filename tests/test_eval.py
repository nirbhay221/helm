"""The evaluation harness runs and produces sane, honest numbers.

These are structural checks (the harness works, metrics are finite, the fair
comparison is wired up), not a claim that Helm wins: the harness exists to tell
the truth, including where Helm loses.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation import (  # noqa: E402
    base_stock_policy,
    evaluate,
    helm_policy,
    helm_verified_policy,
    make_scenarios,
    run_policy,
)
from helm_core import ControllerParams, RecedingHorizonController  # noqa: E402


def test_same_seed_gives_identical_demand_for_fair_comparison():
    sc = make_scenarios(1, seed=1)[0]
    s1, s2 = sc.fresh_sim(), sc.fresh_sim()
    run_policy(s1, base_stock_policy())
    run_policy(s2, helm_policy(RecedingHorizonController(ControllerParams())))
    # demand is independent of ordering decisions, so both face the same path
    assert [o.demand for o in s1.history] == [o.demand for o in s2.history]


def test_metrics_are_finite_and_in_range():
    sc = make_scenarios(1, seed=2)[0]
    m = run_policy(sc.fresh_sim(), helm_policy(RecedingHorizonController(ControllerParams())))
    assert m.cum_abs_deviation >= 0
    assert 0.0 <= m.fill_rate <= 1.0
    assert m.stockout_periods >= 0
    assert m.avg_inventory >= 0


def test_verifier_does_not_increase_cash_breaches():
    sc = make_scenarios(1, seed=3)[0]
    c = RecedingHorizonController(ControllerParams(lead_time=sc.params.lead_time,
                                                   cash_floor=sc.params.cash_floor))
    raw = run_policy(sc.fresh_sim(), helm_policy(c))
    gated = run_policy(sc.fresh_sim(), helm_verified_policy(c))
    assert gated.cash_floor_breaches <= raw.cash_floor_breaches


def test_evaluate_reports_both_wins_and_losses():
    s = evaluate(n=30, seed=0)
    assert s["n_scenarios"] == 30
    # the deviation win is expected (it's the controller's objective)...
    assert s["helm_deviation_win_rate"] >= 0.5
    # ...and the report must carry the non-circular, less-flattering metrics too
    for key in ("helm_mean_fill", "base_stock_mean_fill", "helm_mean_avg_inventory",
                "base_stock_mean_avg_inventory", "helm_total_cash_breaches",
                "helm_verified_total_cash_breaches", "n_losses_vs_base"):
        assert key in s
