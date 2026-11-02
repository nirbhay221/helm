"""The marketplace dashboard data builder and page render are well-formed."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.data import build_dashboard_data  # noqa: E402
from ui.page import render_page  # noqa: E402


def test_dashboard_data_is_complete_and_serializable():
    d = build_dashboard_data()
    for key in ("context", "gmv", "cashflow", "creator_wait", "frontier",
                "payout_runs", "payout_engine", "headline"):
        assert key in d
    # the frontier: Helm carries far less reserve shortfall than paying everyone
    fr = d["frontier"]
    assert fr["helm"]["reserve_shortfall"] < fr["pay_all"]["reserve_shortfall"]
    assert fr["helm"]["avg_wait"] < fr["monthly"]["avg_wait"]
    assert fr["helm"]["cash_floor_breaches"] == 0
    # equal-length series for charting
    g = d["gmv"]
    assert len(g["periods"]) == len(g["forecast"]) == len(g["actual"])
    # real-shaped payout batches to creators, some possibly held for approval
    assert d["payout_runs"] and all(r["recipients"] for r in d["payout_runs"])
    # fully JSON-serializable (it is sent to the browser)
    json.dumps(d)


def test_page_renders_with_embedded_data():
    html = render_page(embedded_data=build_dashboard_data())
    assert "<!doctype html>" in html.lower()
    assert "__CHART_JS__" not in html           # placeholder fully replaced
    assert "window.HELM_DATA=" in html
    assert html.count("<canvas") == 5


def test_page_renders_for_live_server_without_embedded_data():
    html = render_page()
    assert "window.HELM_DATA" in html           # falls back to fetch('/api/data')
    assert "/api/data" in html
