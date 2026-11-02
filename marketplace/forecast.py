"""A small, dependency-free time-series forecaster for GMV.

The controller used to plan against a flat line, which is barely a forecast. The
evidence says to start with a strong classical method, so this is Holt's linear
exponential smoothing (the ETS family): it tracks a level and a trend from the
realized history and projects them, with light damping so a noisy spike does not
send the trend running away. Crucially it also returns an uncertainty band from
the one-step forecast errors, growing with the horizon, which is what the
controller needs to size a safety buffer (the chance-constrained upgrade): hold
more reserve when the forecast is less certain.

This is the honest baseline, not the last word. A foundation model
(Chronos/TimesFM) could be benchmarked against it later on real backtests; the
interface (mean + sigma per horizon step) stays the same.
"""
from __future__ import annotations

from dataclasses import dataclass
from statistics import pstdev


@dataclass
class ETSForecaster:
    alpha: float = 0.5        # level smoothing
    beta: float = 0.1         # trend smoothing
    phi: float = 0.9          # trend damping
    level: float = 0.0
    trend: float = 0.0
    resid_std: float = 0.0
    fitted: bool = False

    def fit(self, series) -> "ETSForecaster":
        ys = [float(x) for x in series]
        if not ys:
            self.level, self.trend, self.resid_std, self.fitted = 0.0, 0.0, 0.0, True
            return self
        if len(ys) == 1:
            self.level, self.trend, self.resid_std, self.fitted = ys[0], 0.0, 0.0, True
            return self
        level, trend = ys[0], ys[1] - ys[0]
        resids = []
        for y in ys[1:]:
            pred = level + self.phi * trend
            resids.append(y - pred)
            new_level = self.alpha * y + (1 - self.alpha) * (level + self.phi * trend)
            trend = self.beta * (new_level - level) + (1 - self.beta) * self.phi * trend
            level = new_level
        self.level = level
        self.trend = trend
        self.resid_std = pstdev(resids) if len(resids) > 1 else abs(resids[-1]) if resids else 0.0
        self.fitted = True
        return self

    def forecast(self, horizon: int) -> tuple[list[float], list[float]]:
        """Return (means, sigmas) for the next `horizon` steps."""
        means, sigmas = [], []
        damp = 0.0
        for i in range(1, horizon + 1):
            damp += self.phi ** i
            means.append(max(0.0, self.level + self.trend * damp))
            sigmas.append(self.resid_std * (i ** 0.5))
        return means, sigmas
