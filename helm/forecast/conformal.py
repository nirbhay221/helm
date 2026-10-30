"""Demand forecast with calibrated uncertainty bands.

A damped Holt model gives the point forecast. Split-conformal calibration on its own
one-step-ahead errors gives a band with a coverage guarantee that does not depend on
the model being right, which is what the Navigator needs to plan for the spread.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class DemandAdjustment:
    """A shift the Lookout read from text, e.g. a viral video. Only applied after the Evidence gate passes it."""

    start_week: int
    weeks: int
    multiplier: float


@dataclass(frozen=True)
class Forecast:
    start_week: int
    point: np.ndarray
    lo: np.ndarray
    hi: np.ndarray
    coverage: float

    def scenarios(self) -> list[tuple[float, np.ndarray]]:
        """Low, middle and high demand paths with weights, for the Navigator's robust plan."""
        return [(0.25, self.lo), (0.5, self.point), (0.25, self.hi)]


def _holt(y: np.ndarray, alpha: float, beta: float, phi: float) -> tuple[float, float, np.ndarray]:
    level, trend = y[0], 0.0
    one_step = np.empty(len(y))
    one_step[0] = y[0]
    for t in range(1, len(y)):
        one_step[t] = level + phi * trend
        new_level = alpha * y[t] + (1 - alpha) * (level + phi * trend)
        trend = beta * (new_level - level) + (1 - beta) * phi * trend
        level = new_level
    return level, trend, one_step


def _clip_outliers(y: np.ndarray, window: int = 8, k: float = 3.0) -> np.ndarray:
    out = y.copy()
    for t in range(len(y)):
        past = y[max(0, t - window):t] if t >= 4 else y[: max(4, t + 1)]
        med = np.median(past)
        mad = np.median(np.abs(past - med)) * 1.4826 or 0.1 * med
        out[t] = np.clip(y[t], med - k * mad, med + k * mad)
    return out


def baseline(history: list[float], start_week: int, horizon: int, coverage: float = 0.8,
             adjustments: list[DemandAdjustment] | None = None, window: int = 12) -> Forecast:
    """A deliberately different, simpler forecaster for the Validator: recent median and empirical spread.

    The Validator imagines futures with this instead of the producer's forecast, so a mistake
    in the producer's model is not silently shared by the check that is meant to catch it.
    """
    y = np.asarray(history[-window:], dtype=float)
    med = float(np.median(y))
    tail = (1 - coverage) / 2
    lo_r, hi_r = np.quantile(y / med, [tail, 1 - tail])
    point = np.full(horizon, med)
    lo, hi = point * lo_r, point * hi_r
    for adj in adjustments or []:
        for h in range(horizon):
            if adj.start_week <= start_week + h < adj.start_week + adj.weeks:
                point[h] *= adj.multiplier
                lo[h] *= adj.multiplier
                hi[h] *= adj.multiplier
    return Forecast(start_week, point, lo, hi, coverage)


def forecast(
    history: list[float],
    start_week: int,
    horizon: int,
    coverage: float = 0.8,
    adjustments: list[DemandAdjustment] | None = None,
    alpha: float = 0.35,
    beta: float = 0.1,
    phi: float = 0.9,
) -> Forecast:
    raw = np.asarray(history, dtype=float)
    if len(raw) < 4:
        raise ValueError("need at least 4 weeks of history to forecast")
    # Fit the trend on outlier-clipped history so a one-off spike is not extrapolated into
    # a lasting trend (the forecast-side cause of the bullwhip effect). The conformal band
    # is still calibrated on the raw errors, so spike risk stays in the band.
    y = _clip_outliers(raw)
    level, trend, one_step = _holt(y, alpha, beta, phi)

    damp = np.cumsum(phi ** np.arange(1, horizon + 1))
    point = np.maximum(0.0, level + damp * trend)

    # Split conformal: the coverage-quantile of absolute one-step errors, with the finite-sample correction.
    errors = np.abs(raw[1:] - one_step[1:])
    n = len(errors)
    q_level = min(1.0, np.ceil((n + 1) * coverage) / n)
    q = float(np.quantile(errors, q_level))
    width = q * np.sqrt(np.arange(1, horizon + 1))

    lo = np.maximum(0.0, point - width)
    hi = point + width
    for adj in adjustments or []:
        for h in range(horizon):
            if adj.start_week <= start_week + h < adj.start_week + adj.weeks:
                point[h] *= adj.multiplier
                lo[h] *= adj.multiplier
                hi[h] *= adj.multiplier
    return Forecast(start_week, point, lo, hi, coverage)
