"""Split-conformal intervals give the finite-sample quantile, widen with the horizon,
and bracket the point estimate; the PD band comes from the creator's own history."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marketplace.conformal import (  # noqa: E402
    ConformalForecaster, conformal_quantile, pd_uncertainty_band,
)


def test_conformal_quantile_uses_finite_sample_correction():
    scores = [1, 2, 3, 4, 5, 6, 7, 8, 9]          # n=9
    # rank = ceil((9+1)*0.9) = 9 -> the 9th smallest (index 8) = 9
    assert conformal_quantile(scores, 0.1) == 9
    # too few points for 99% coverage -> no guarantee, returns inf
    assert conformal_quantile([1, 2], 0.01) == float("inf")


def test_forecast_band_brackets_mean_and_widens():
    series = [100, 108, 115, 121, 130, 139, 147, 156, 164, 173]
    cf = ConformalForecaster(alpha=0.1).fit(series)
    steps = cf.forecast(series, horizon=4)
    for s in steps:
        assert s["low"] <= s["mean"] <= (s["high"] if s["high"] is not None else float("inf"))
    widths = [s["half_width"] for s in steps if s["half_width"] is not None]
    assert widths[-1] >= widths[0]                 # the band grows with the horizon


def test_pd_band_brackets_the_point_estimate():
    b = pd_uncertainty_band([800, 1200, 900, 1100, 1000, 950], alpha=0.1)
    assert 0.0 <= b["low"] <= b["pd"] <= b["high"] <= 1.0
    assert 0.0 < b["half_width"] <= 0.5
    assert b["coverage"] == 0.9


def test_pd_band_is_wider_for_a_thin_file_than_a_long_steady_one():
    steady = pd_uncertainty_band([1000, 1020, 990, 1010, 1005, 995, 1000, 1015, 985, 1000, 1010, 1000])
    thin = pd_uncertainty_band([1000])
    falling = pd_uncertainty_band([2000, 1800, 1600, 1400, 1200, 1000, 800, 600])
    assert thin["half_width"] > 3 * steady["half_width"]
    assert falling["half_width"] > steady["half_width"]


def test_pd_band_is_reproducible_for_the_same_ledger():
    h = [800, 1200, 900, 1100, 1000, 950]
    assert pd_uncertainty_band(h) == pd_uncertainty_band(h)
