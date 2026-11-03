"""The reinvestment pool: NAV from a real-priced basket, proportional unit stakes."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marketplace.reinvest import BASKET, Holding, ReinvestmentPool, nav_series  # noqa: E402


def _hist(seq):
    return [(1000 + i * 86400, float(v)) for i, v in enumerate(seq)]


def test_nav_series_rebases_to_100_and_tracks_the_basket():
    # one holding doubling -> NAV doubles to 200 at its weight
    histories = {
        "SPY": _hist([100, 110, 120]),   # +20%
        "VNQ": _hist([50, 50, 50]),      # flat
        "MCD": _hist([10, 10, 10]),      # flat
    }
    dates, nav = nav_series(histories, BASKET)
    assert nav[0] == 100.0                               # rebased to 100 at start
    # 50% weight on a +20% asset, rest flat -> +10%
    assert abs(nav[-1] - 110.0) < 1e-6


def test_units_are_proportional_to_contribution():
    pool = ReinvestmentPool(dates=[1, 2], nav=[100.0, 100.0])
    pool.contribute("a", 100.0, at=0)
    pool.contribute("b", 300.0, at=0)
    # b put in 3x, so b holds 3x the units and 3x the stake
    assert abs(pool.stake_value("b") - 3 * pool.stake_value("a")) < 1e-6


def test_stake_value_moves_with_nav():
    pool = ReinvestmentPool(dates=[1, 2], nav=[100.0, 120.0])
    pool.contribute("a", 100.0, at=0)     # 1 unit at NAV 100
    assert abs(pool.stake_value("a") - 120.0) < 1e-6     # now worth 120 (+20%)
    assert pool.total_value() >= pool.total_contributed()
