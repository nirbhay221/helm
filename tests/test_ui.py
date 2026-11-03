"""The agent-centric dashboard data builder and page render are well-formed."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.data import build_dashboard_data  # noqa: E402
from ui.page import render_page  # noqa: E402


def test_dashboard_data_is_complete_and_serializable():
    d = build_dashboard_data()
    for key in ("context", "gmv", "cashflow", "risk", "journal", "frontier",
                "payout_engine", "headline"):
        assert key in d
    # the agent ran real cycles and paid creators
    assert d["headline"]["cycles"] >= 1
    assert d["journal"] and any(j["paid"] for j in d["journal"])
    # the agent raised its risk posture on the fraud signal cycle
    rk = d["risk"]
    i = rk["periods"].index(rk["signal_cycle"])
    assert rk["risk_multiplier"][i] > 1.0
    # equal-length forecast series
    g = d["gmv"]
    assert len(g["periods"]) == len(g["actual"]) == len(g["forecast"])
    # Helm holds less reserve shortfall than paying everyone
    fr = d["frontier"]
    assert fr["helm"]["reserve_shortfall"] < fr["pay_all"]["reserve_shortfall"]
    json.dumps(d)


def test_page_renders_with_embedded_data():
    html = render_page(embedded_data=build_dashboard_data())
    assert "<!doctype html>" in html.lower()
    assert "__CHART_JS__" not in html
    assert "window.HELM_DATA=" in html
    assert html.count("<canvas") == 5


def test_page_renders_for_live_server_without_embedded_data():
    html = render_page()
    assert "window.HELM_DATA" in html
    assert "/api/data" in html
