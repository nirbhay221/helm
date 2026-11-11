"""Small, dependency-light statistical models shared by the engine.

Two reusable primitives, both hand-rolled on numpy so they run anywhere the
engine runs (no scikit-learn or statsmodels, which are not on the host):

  * holt_winters: exponential smoothing with a linear trend (Holt) and an
    optional additive season, with the smoothing constants chosen by a small
    grid search that minimises one-step error. Used to forecast a creator's
    earnings so recommendations look forward, not just back.

  * LogisticModel: a tiny logistic-regression scorecard (standardise, then
    full-batch gradient descent with L2). Used for the advance default-risk
    score and the fraud-ring link probability, so those are calibrated models
    fit to data rather than hand-tuned formulas.

Everything is deterministic: fixed iterations, fixed seeds, no wall-clock. The
models expose a .predict_proba so a real label set can be dropped in later with
no change to the callers.
"""
from __future__ import annotations

import numpy as np


# --- forecasting -----------------------------------------------------------

def _init_state(x):
    """Seed level and trend from a least-squares line over the history rather than the
    first two points: a first difference on noisy data is mostly noise, and a slow trend
    constant then carries it for the whole series (a flat but noisy history would read as
    steady growth or collapse)."""
    n = len(x)
    if n < 2:
        return float(x[0]), 0.0
    t = np.arange(n, dtype=float)
    slope, intercept = np.polyfit(t, np.asarray(x, dtype=float), 1)
    return float(intercept), float(slope)


def _sse(series, alpha, beta, season, L):
    """One-step-ahead squared error for given smoothing constants."""
    x = series
    level, trend = _init_state(x)
    seas = list(season) if season is not None else None
    err = 0.0
    for t in range(1, len(x)):
        s_t = seas[t % L] if seas is not None else 0.0
        pred = level + trend + s_t
        err += (x[t] - pred) ** 2
        prev_level = level
        if seas is not None:
            level = alpha * (x[t] - s_t) + (1 - alpha) * (level + trend)
            seas[t % L] = beta * (x[t] - level) + (1 - beta) * s_t
        else:
            level = alpha * x[t] + (1 - alpha) * (level + trend)
        trend = beta * (level - prev_level) + (1 - beta) * trend
    return err


def holt_winters(series, horizon: int = 4, season_length: int | None = None) -> dict:
    """Forecast `horizon` steps ahead with Holt (linear trend), optional additive
    season. Smoothing constants are grid-searched to minimise one-step error, so
    a flat history yields a flat forecast and a trending one carries its trend."""
    x = np.asarray([float(v) for v in series], dtype=float)
    n = len(x)
    if n == 0:
        return {"next": 0.0, "path": [0.0] * horizon, "trend": 0.0, "level": 0.0,
                "direction": "flat", "pct_change": 0.0, "model": "none"}
    if n < 3:
        last = float(x[-1])
        return {"next": last, "path": [last] * horizon, "trend": 0.0, "level": last,
                "direction": "flat", "pct_change": 0.0, "model": "last-value"}

    use_season = bool(season_length and n >= 2 * season_length)
    L = int(season_length) if use_season else 1
    season0 = None
    if use_season:
        # seed each season index with its deviation from the first-cycle mean
        first = x[:L]
        season0 = [float(v - first.mean()) for v in first]

    grid = np.linspace(0.1, 0.9, 9)
    best, best_err = (0.5, 0.3), float("inf")
    for a in grid:
        for b in grid:
            e = _sse(x, a, b, list(season0) if season0 is not None else None, L)
            if e < best_err:
                best_err, best = e, (float(a), float(b))
    alpha, beta = best

    # run the recursion once with the chosen constants to get final state
    level, trend = _init_state(x)
    seas = list(season0) if season0 is not None else None
    for t in range(1, n):
        prev_level = level
        if seas is not None:
            s_t = seas[t % L]
            level = alpha * (x[t] - s_t) + (1 - alpha) * (level + trend)
            seas[t % L] = beta * (x[t] - level) + (1 - beta) * s_t
        else:
            level = alpha * x[t] + (1 - alpha) * (level + trend)
        trend = beta * (level - prev_level) + (1 - beta) * trend

    path = []
    for h in range(1, horizon + 1):
        s_h = seas[(n + h - 1) % L] if seas is not None else 0.0
        path.append(round(float(max(0.0, level + h * trend + s_h)), 2))
    nxt = path[0] if path else round(float(level), 2)
    base = float(x[-1]) if x[-1] else (float(level) or 1.0)
    pct = round(float((nxt - base) / abs(base) * 100), 1) if base else 0.0
    tol = max(1e-6, 0.01 * abs(float(level)))          # under 1% of the level a week is flat
    direction = "up" if trend > tol else ("down" if trend < -tol else "flat")
    return {"next": float(nxt), "path": path, "trend": round(float(trend), 3),
            "level": round(float(level), 2), "direction": direction,
            "pct_change": pct, "model": "holt-winters" if seas is not None else "holt"}


# --- logistic scorecard ----------------------------------------------------

class LogisticModel:
    """A minimal logistic regression: standardise features, then full-batch
    gradient descent with L2. Deterministic given the same data."""

    def __init__(self, l2: float = 1.0, lr: float = 0.3, iters: int = 4000):
        self.l2, self.lr, self.iters = l2, lr, iters
        self.mu = self.sd = self.w = None
        self.b = 0.0

    def fit(self, X, y) -> "LogisticModel":
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        self.mu = X.mean(axis=0)
        self.sd = X.std(axis=0)
        self.sd[self.sd == 0] = 1.0
        Z = (X - self.mu) / self.sd
        n, d = Z.shape
        self.w = np.zeros(d)
        self.b = 0.0
        for _ in range(self.iters):
            p = 1.0 / (1.0 + np.exp(-(Z @ self.w + self.b)))
            g = p - y
            gw = Z.T @ g / n + self.l2 * self.w / n
            gb = g.mean()
            self.w -= self.lr * gw
            self.b -= self.lr * gb
        return self

    def predict_proba(self, x) -> float:
        z = (np.asarray(x, dtype=float) - self.mu) / self.sd
        return float(1.0 / (1.0 + np.exp(-(z @ self.w + self.b))))
