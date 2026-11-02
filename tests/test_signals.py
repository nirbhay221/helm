"""The signal desk and its verifier: the LLM informs the forecast, bounded.

These tests are keyless and deterministic: they exercise the fallback parser,
the verifier's bounds, and the end effect (a verified signal lets the controller
pre-position stock and avoid stockouts a flat forecast walks into). The live
model path is exercised by scripts/demo_signal.py.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.signals import ForecastAdjustment, SignalDesk  # noqa: E402
from agent.verifier import ActionVerifier  # noqa: E402
from arms.awardsmith import DiscountTier, SupplierQuote  # noqa: E402
from evaluation import helm_policy, helm_signal_policy, run_policy  # noqa: E402
from helm_core import ControllerParams, RecedingHorizonController  # noqa: E402
from simulator import BusinessParams, BusinessSim  # noqa: E402
from simulator.real_demand import P263_WEEKLY, PLANNED_DEMAND  # noqa: E402


def _suppliers():
    return [
        SupplierQuote("Alpha", [DiscountTier(0, 9.0)], capacity=400),
        SupplierQuote("Beta", [DiscountTier(0, 8.5), DiscountTier(40, 8.0)], capacity=400),
        SupplierQuote("Gamma", [DiscountTier(50, 7.5)], capacity=300),
    ]


def _params():
    return BusinessParams(
        price=20.0, unit_cost=8.0, lead_time=2,
        init_inventory=40.0, init_cash=4000.0, target_inventory=40.0,
        cash_floor=0.0, baseline_demand=PLANNED_DEMAND,
        demand_series=list(P263_WEEKLY),
    )


def _verifier():
    controller = RecedingHorizonController(ControllerParams(horizon=8, lead_time=2))
    return ActionVerifier(BusinessSim(_params(), seed=7, n_periods=52), controller, _suppliers())


def test_fallback_parser_reads_period_and_magnitude():
    desk = SignalDesk(llm=None)  # no key -> fallback
    adj = desk._interpret_fallback("promo in week 24, demand will triple", 22, 17.0, 8)
    assert 24 in adj.period_deltas
    assert abs(adj.period_deltas[24] - 34.0) < 1e-6  # triple of 17 = +34
    assert adj.source == "fallback"


def test_verifier_discards_adjustment_with_no_cited_signal():
    v = _verifier()
    adj = ForecastAdjustment(period_deltas={24: 34.0}, cited_signal="")
    verdict, clean = v.verify_forecast_adjustment(adj, 22, 17.0, horizon=8)
    assert verdict.ok is False
    assert clean.is_empty()


def test_verifier_clamps_oversized_and_out_of_window_deltas():
    v = _verifier()
    adj = ForecastAdjustment(
        period_deltas={24: 999.0, 99: 20.0},  # too big; and outside the window
        cited_signal="promo week 24",
    )
    verdict, clean = v.verify_forecast_adjustment(adj, 22, 17.0, horizon=8, max_factor=3.0)
    assert 99 not in clean.period_deltas                      # dropped (out of window)
    assert clean.period_deltas[24] == 51.0                    # clamped to 3x baseline
    assert verdict.repaired is True


def test_verified_signal_avoids_stockouts_a_flat_forecast_suffers():
    controller = RecedingHorizonController(
        ControllerParams(horizon=8, unit_cost=8.0, price=20.0, lead_time=2))
    # hand-built verified adjustment (the promo surge at week 24)
    adj = ForecastAdjustment(period_deltas={24: 34.0}, cited_signal="promo week 24")

    m_helm = run_policy(BusinessSim(_params(), seed=7, n_periods=52), helm_policy(controller))
    m_sig = run_policy(BusinessSim(_params(), seed=7, n_periods=52),
                       helm_signal_policy(controller, adj))

    assert m_sig.stockout_periods <= m_helm.stockout_periods
    assert m_sig.fill_rate >= m_helm.fill_rate
    assert m_sig.stockout_periods == 0        # the signal fully prevents the promo stockout
