"""Product search falls back to a deterministic catalog with no key, respects a price
cap, narrows by query, and reports whether the live Channel3 backend is configured."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market.shopping import Channel3Client  # noqa: E402


def test_no_key_uses_demo_catalog():
    c = Channel3Client(env={})
    assert c.available is False
    products, backend = c.search("microphone", limit=6)
    assert backend == "demo-catalog"
    assert len(products) >= 1
    assert all({"title", "price", "merchant", "currency"} <= set(p) for p in products)


def test_query_narrows_results():
    c = Channel3Client(env={})
    products, _ = c.search("microphone", limit=8)
    assert any("microphone" in p["title"].lower() for p in products)


def test_price_cap_filters():
    c = Channel3Client(env={})
    products, _ = c.search("", max_price=50, limit=8)
    assert products and all(p["price"] <= 50 for p in products)


def test_key_present_marks_available():
    c = Channel3Client(env={"CHANNEL3_API_KEY": "sk_test_123"})
    assert c.available is True      # live path is attempted; network not exercised in tests


def test_unmatched_query_still_returns_catalog():
    c = Channel3Client(env={})
    products, backend = c.search("zzz-nothing-matches-this", limit=6)
    assert backend == "demo-catalog" and len(products) >= 1
