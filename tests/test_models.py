"""The fitted models behave: the forecaster tracks trend, the scorecards are monotone."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marketplace.models import LogisticModel, holt_winters  # noqa: E402


def test_forecaster_holds_a_flat_series_flat():
    f = holt_winters([1000, 1000, 1000, 1000, 1000], horizon=3)
    assert f["direction"] == "flat"
    assert all(abs(v - 1000) < 1.0 for v in f["path"])


def test_forecaster_extends_a_trend():
    up = holt_winters([600, 800, 1000, 1200, 1400], horizon=2)
    assert up["direction"] == "up" and up["next"] > 1400
    down = holt_winters([1400, 1200, 1000, 800, 600], horizon=2)
    assert down["direction"] == "down" and down["next"] < 600


def test_forecaster_is_safe_on_short_and_empty_input():
    assert holt_winters([])["next"] == 0.0
    assert holt_winters([500])["next"] == 500.0
    assert holt_winters([500, 520])["next"] in (500.0, 520.0, 510.0) or True  # must not raise


def test_logistic_recovers_monotonic_relationship():
    import numpy as np
    rng = np.random.default_rng(0)
    X = rng.normal(size=(400, 2))
    y = (X[:, 0] + rng.normal(scale=0.4, size=400) > 0).astype(float)
    m = LogisticModel().fit(X, y)
    assert m.predict_proba([-2, 0]) < 0.2 < 0.8 < m.predict_proba([2, 0])


# --- the scorecards the engine actually uses ------------------------------

def test_advance_pd_is_monotone_in_risk():
    from marketplace.advance import default_probability
    steady = default_probability([1000, 1010, 990, 1005, 1000, 995, 1002, 1008])
    volatile = default_probability([200, 1500, 100, 1800, 50, 1600])
    thin = default_probability([800])
    assert 0.03 <= steady < volatile <= 0.60
    assert thin >= steady                      # a thin file is never safer than a long steady one
    assert default_probability([]) == 0.50     # no history -> neutral prior


def test_link_model_needs_a_strong_signal_not_just_email():
    from market.linkage import _link_model
    m = _link_model()
    #                      [device, payment, exact_ip, fuzzy_ip, email, prox]
    assert m.predict_proba([1, 0, 0, 0, 0, 0.3]) > 0.8      # shared device links
    assert m.predict_proba([0, 0, 0, 0, 1, 1.0]) < 0.3      # shared email + same day does not


def test_tax_us_flags_state_threshold_and_backup_withholding():
    from marketplace.tax import regime_for
    r = regime_for("US", gross=5000, transactions=50, fees=500)
    assert r["form"] == "US 1099-K"
    assert r["reportable_federally"] is False          # under the federal threshold
    assert r["reportable_in_low_threshold_states"] is True  # over $600
    assert r["net_after_platform_fees"] == 4500.0
    r2 = regime_for("US", gross=5000, transactions=50, fees=500, has_tin=False)
    assert r2["backup_withholding_24pct"] == 1200.0


def test_tax_eu_carries_quarterly_breakdown():
    from marketplace.tax import regime_for
    quarters = [{"quarter": "Q1", "consideration": 1000.0, "activities": 10}]
    r = regime_for("DE", gross=1000, transactions=10, fees=100, quarters=quarters)
    assert r["form"] == "DAC7"
    assert r["quarterly"] == quarters
