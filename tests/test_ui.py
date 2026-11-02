"""The dashboard data builder and page render are well-formed."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.data import build_dashboard_data  # noqa: E402
from ui.page import render_page  # noqa: E402


def test_dashboard_data_is_complete_and_serializable():
    d = build_dashboard_data()
    for key in ("variance", "inventory", "cash", "journal", "awardsmith",
                "payout_engine", "evaluation", "signal", "cumulative_deviation"):
        assert key in d
    # the signal panel: the verified LLM forecast bump drives stockouts to zero
    sig = d["signal"]
    assert sig["verified"] is True
    assert sig["policies"]["helm_signal"]["stockouts"] == 0
    assert sig["policies"]["helm_signal"]["lost_units"] <= sig["policies"]["helm"]["lost_units"]
    # the money shot: Helm closes far more variance than an uncontrolled business
    cd = d["cumulative_deviation"]
    assert cd["helm"] < cd["uncontrolled"]
    # equal-length series for charting
    v = d["variance"]
    assert len(v["periods"]) == len(v["forecast_demand"]) == len(v["actual_demand"])
    # the demand driving the demo is the REAL recorded series, not synthetic
    from simulator.real_demand import P263_WEEKLY
    assert v["actual_demand"] == [float(x) for x in P263_WEEKLY]
    assert "UCI" in v["source"]
    # fully JSON-serializable (it is sent to the browser)
    json.dumps(d)


def test_page_renders_with_embedded_data():
    html = render_page(embedded_data=build_dashboard_data())
    assert "<!doctype html>" in html.lower()
    assert "__CHART_JS__" not in html           # placeholder fully replaced
    assert "window.HELM_DATA=" in html
    assert html.count("<canvas") == 7


def test_page_renders_for_live_server_without_embedded_data():
    html = render_page()
    assert "window.HELM_DATA" in html           # falls back to fetch('/api/data')
    assert "/api/data" in html
