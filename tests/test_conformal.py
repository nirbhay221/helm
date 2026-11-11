"""Split-conformal intervals give the finite-sample quantile, widen with the horizon,
and bracket the point estimate; the PD band brackets the scorecard's probability."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marketplace.conformal import (  # noqa: E402
    ConformalForecaster, conformal_pd_band, conformal_quantile,
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
    b = conformal_pd_band([800, 1200, 900, 1100, 1000, 950], alpha=0.1)
    assert 0.0 <= b["low"] <= b["pd"] <= b["high"] <= 1.0
    assert 0.0 < b["half_width"] <= 0.5
    assert b["coverage"] == 0.9
