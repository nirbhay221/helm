"""The global dashboard data builder and page render are well-formed."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.data import build_dashboard_data  # noqa: E402
from ui.page import render_page  # noqa: E402


def test_dashboard_data_is_complete_and_serializable():
    d = build_dashboard_data()
    for key in ("context", "population", "scenarios", "reinvest", "directory", "payout_engine", "headline"):
        assert key in d
    ri = d["reinvest"]
    assert ri["holdings"] and ri["nav"]["values"] and len(ri["nav"]["dates"]) == len(ri["nav"]["values"])
    dr = d["directory"]
    assert dr["total"] >= 5000 and dr["sample"]        # scale plus browsable individuals
    assert all(c.get("display") and c.get("country") for c in dr["sample"])
    assert d["headline"]["creators"] == dr["total"]
    assert d["headline"]["creators"] >= 1000           # real-world scale
    s = d["scenarios"]
    assert len(s) >= 2
    for sc in s:
        assert "weights" in sc and "constraints" in sc and "by_country" in sc
        assert sc["paid_count"] >= 0
    # a country-freeze policy actually excludes countries
    assert any(sc["constraints"]["exclude_countries"] for sc in s)
    json.dumps(d)


def test_page_renders_with_embedded_data():
    html = render_page(embedded_data=build_dashboard_data())
    assert "<!doctype html>" in html.lower()
    assert "__CHART_JS__" not in html                  # placeholder replaced
    assert "window.HELM_DATA=" in html
    assert 'id="countryChart"' in html                 # payouts-by-country chart
    assert 'id="navChart"' in html                     # the reinvestment NAV chart
    assert html.count("<canvas") == 4


def test_page_renders_for_live_server_without_embedded_data():
    html = render_page()
    assert "window.HELM_DATA" in html
    assert "/api/data" in html
