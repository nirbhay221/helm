"""Distribution-free prediction intervals via split conformal prediction.

The forecaster and the default scorecard both emitted point estimates (or a naive
residual band). Point estimates are dangerous for money: they let the system lend
or release as if it were certain. Split conformal prediction wraps any point
predictor in an interval with a *finite-sample marginal coverage guarantee* and no
distributional assumption: hold out a calibration set, score the nonconformity
(absolute error) on it, and the (1-alpha) conformal quantile is the half-width that
covers the next point with probability at least 1-alpha.

We use it two ways:
  - demand forecasting: calibrated bands that widen honestly under noise, so the
    controller holds more reserve when the forecast is genuinely less certain;
  - default risk: a conformal band on the probability of default, so an advance is
    sized DOWN when the estimate is uncertain, not only when it is high.

Grounded in split conformal prediction (Vovk; Lei et al. "Distribution-Free
Predictive Inference"), applied to lending the way the loan-approval and
VaR conformal literature does. Pure-python, numpy-optional, so it runs on the box.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


def conformal_quantile(scores, alpha: float) -> float:
    """The split-conformal quantile of nonconformity scores at level alpha.

    Uses the finite-sample correction: the ceil((n+1)(1-alpha))/n empirical quantile,
    which is what gives the >= 1-alpha marginal coverage guarantee. Returns +inf when
    the calibration set is too small to guarantee coverage (honest: no claim made)."""
    s = sorted(float(x) for x in scores)
    n = len(s)
    if n == 0:
        return float("inf")
    rank = math.ceil((n + 1) * (1.0 - alpha))
    if rank > n:
        return float("inf")          # not enough calibration points for this alpha
    return s[rank - 1]


@dataclass
class ConformalForecaster:
    """Wraps a mean/sigma forecaster (the ETS one) with calibrated intervals.

    Splits the history into a training part and a calibration part, fits the base
    forecaster on training, measures one-step nonconformity on calibration, and uses
    the conformal quantile to set the band half-width. The band still grows with the
    horizon (sqrt-time, matching error accumulation), but its scale is calibrated to
    realized errors rather than assumed Gaussian."""
    alpha: float = 0.1               # 90% coverage
    cal_frac: float = 0.3            # last 30% of history held out for calibration
    q: float = 0.0
    covered_note: str = ""

    def fit(self, series) -> "ConformalForecaster":
        from .forecast import ETSForecaster
        ys = [float(x) for x in series]
        n = len(ys)
        if n < 6:
            # too short to split; fall back to the residual std as a rough band
            f = ETSForecaster().fit(ys)
            self.q = f.resid_std if f.resid_std > 0 else (abs(ys[-1]) * 0.1 if ys else 0.0)
            self.covered_note = "short series: uncalibrated residual band"
            return self
        n_cal = max(2, int(round(n * self.cal_frac)))
        train, cal = ys[:n - n_cal], ys[n - n_cal:]
        base = ETSForecaster().fit(train)
        # one-step-ahead nonconformity across the calibration tail
        scores = []
        lvl, trd = base.level, base.trend
        a, b, phi = base.alpha, base.beta, base.phi
        for y in cal:
            pred = lvl + phi * trd
            scores.append(abs(y - pred))
            new_lvl = a * y + (1 - a) * (lvl + phi * trd)
            trd = b * (new_lvl - lvl) + (1 - b) * phi * trd
            lvl = new_lvl
        self.q = conformal_quantile(scores, self.alpha)
        if not math.isfinite(self.q):
            # too few calibration points for this coverage level: fall back to a
            # residual-std band and say so, rather than claiming an infinite interval.
            from statistics import pstdev
            self.q = pstdev(scores) if len(scores) > 1 else (scores[-1] if scores else 0.0)
            self.covered_note = (f"insufficient calibration ({len(scores)} pts) for "
                                 f"{int((1 - self.alpha) * 100)}% coverage; residual-std band")
        else:
            self.covered_note = (f"calibrated on {len(scores)} points, target "
                                 f"{int((1 - self.alpha) * 100)}% coverage")
        return self

    def forecast(self, series, horizon: int):
        """Return dicts per step: {mean, low, high, half_width}. Refits the base on the
        full series for the point forecast, scales the conformal band by sqrt(step)."""
        from .forecast import ETSForecaster
        if self.q == 0.0 and not self.covered_note:
            self.fit(series)
        means, _ = ETSForecaster().fit([float(x) for x in series]).forecast(horizon)
        out = []
        for i, m in enumerate(means, start=1):
            hw = self.q * math.sqrt(i) if math.isfinite(self.q) else float("inf")
            lo = max(0.0, m - hw) if math.isfinite(hw) else 0.0
            hi = m + hw if math.isfinite(hw) else float("inf")
            out.append({"step": i, "mean": round(m, 2),
                        "low": round(lo, 2), "high": round(hi, 2) if math.isfinite(hi) else None,
                        "half_width": round(hw, 2) if math.isfinite(hw) else None})
        return out


PRIOR_CV = 0.5          # what we assume about month-to-month swings before seeing any
PRIOR_MONTHS = 2.0      # how many months of evidence that assumption is worth
AHEAD = 6               # "how far could the estimate move over the next six months?"


def pd_uncertainty_band(history, alpha: float = 0.1, draws: int = 400) -> dict:
    """How much a creator's default-risk estimate could still move, from THEIR OWN history.

    A parametric bootstrap: fit the creator's level, swings (coefficient of variation) and
    trend, shrunk toward a prior when the file is thin; simulate the next six months many
    times; re-score default risk on observed + simulated months; the central (1 - alpha)
    range of those scores is the band. A short or volatile history moves a lot when more
    months arrive (wide band, smaller advance); a long steady one barely moves (narrow band).
    Seeded from the history, so the same ledger always gets the same band.
    Returns {pd, low, high, half_width, coverage, method}."""
    from .advance import default_probability
    xs = [float(x) for x in (history or []) if x is not None]
    pd_point = default_probability(xs)
    try:
        import hashlib

        import numpy as np
        n = len(xs)
        arr = np.asarray(xs, dtype=float) if n else np.asarray([0.0])
        mean = float(arr.mean()) if n else 0.0
        if n == 0 or mean <= 0:
            raise ValueError("no positive history")
        cv_obs = float(arr.std() / mean) if n > 1 else PRIOR_CV
        cv = (n * cv_obs + PRIOR_MONTHS * PRIOR_CV) / (n + PRIOR_MONTHS)
        slope = float(np.polyfit(np.arange(n), arr, 1)[0] / mean) if n > 2 else 0.0
        slope *= n / (n + PRIOR_MONTHS)
        seed = int(hashlib.sha256(",".join(f"{x:.2f}" for x in xs).encode()).hexdigest()[:8], 16)
        rng = np.random.default_rng(seed)
        level = float(np.mean(arr[-3:]))
        sims = []
        for _ in range(draws):
            # the swings themselves are uncertain when there are few months to judge them by
            cv_d = cv * float(np.sqrt(rng.chisquare(n + PRIOR_MONTHS) / (n + PRIOR_MONTHS)))
            fut = [max(0.0, level * (1 + slope * (t + 1)) * (1 + rng.normal(0, cv_d))) for t in range(AHEAD)]
            sims.append(default_probability(xs + fut))
        low = float(np.quantile(sims, alpha / 2))
        high = float(np.quantile(sims, 1 - alpha / 2))
        low, high = min(low, pd_point), max(high, pd_point)
    except Exception:
        low, high = max(0.0, pd_point - 0.15), min(1.0, pd_point + 0.15)   # no data: a wide, honest default
    return {"pd": pd_point, "low": round(low, 3), "high": round(high, 3), "half_width": round((high - low) / 2, 3),
            "coverage": round(1.0 - alpha, 2), "method": "bootstrap over the creator's own history"}
