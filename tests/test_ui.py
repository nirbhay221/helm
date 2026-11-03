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
    for key in ("context", "population", "scenarios", "payout_engine", "headline"):
        assert key in d
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
    for ph in ("__CHART_JS__", "__VMAP_CSS__", "__VMAP_JS__", "__VMAP_WORLD__"):
        assert ph not in html                          # all placeholders replaced
    assert "window.HELM_DATA=" in html
    assert 'id="worldmap"' in html                     # the world choropleth
    assert html.count("<canvas") == 2


def test_page_renders_for_live_server_without_embedded_data():
    html = render_page()
    assert "window.HELM_DATA" in html
    assert "/api/data" in html
