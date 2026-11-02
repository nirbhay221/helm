"""The ETS forecaster tracks level and trend and reports horizon uncertainty."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marketplace.forecast import ETSForecaster  # noqa: E402


def test_flat_series_forecasts_flat_with_small_uncertainty():
    f = ETSForecaster().fit([100.0] * 10)
    means, sigmas = f.forecast(4)
    assert all(abs(m - 100.0) < 1.0 for m in means)
    assert all(s < 1.0 for s in sigmas)


def test_rising_series_forecasts_upward():
    f = ETSForecaster().fit([10, 20, 30, 40, 50, 60])
    means, _ = f.forecast(3)
    assert means[0] > 55                    # projects the upward trend
    assert means[2] >= means[0]


def test_uncertainty_grows_with_horizon_and_noise():
    noisy = [100, 60, 140, 80, 120, 70, 130, 90]
    f = ETSForecaster().fit(noisy)
    means, sigmas = f.forecast(5)
    assert sigmas[0] > 0
    assert sigmas[-1] > sigmas[0]           # the band widens with the horizon
    assert all(m >= 0 for m in means)       # never forecasts negative GMV
