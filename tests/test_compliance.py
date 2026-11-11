"""Outbound screening blocks sanctioned payees and structuring, holds on velocity and
duplicates, and clears a normal payment."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market.compliance import ComplianceEngine  # noqa: E402


def test_clean_payment_allowed():
    out = ComplianceEngine().screen("Ava", 500.0, now=1000.0)
    assert out["decision"] == "allow" and out["reasons"] == ["clean"]


def test_sanctioned_payee_blocked():
    out = ComplianceEngine().screen("Blocked Payee", 50.0, now=1000.0)
    assert out["decision"] == "block" and any("sanctions" in r for r in out["reasons"])


def test_structuring_is_detected():
    e = ComplianceEngine()
    e.screen("Smurf", 6000.0, now=1000.0)
    out = e.screen("Smurf", 5000.0, now=1100.0)        # sub-threshold but sums to 11000 in window
    assert out["decision"] == "block" and any("structuring" in r for r in out["reasons"])


def test_velocity_holds():
    e = ComplianceEngine()
    for i in range(5):
        e.screen("Fast", 10.0 + i, now=1000.0 + i)      # 5 prior payments
    out = e.screen("Fast", 99.0, now=1006.0)            # the 6th in the window
    assert out["decision"] in ("hold", "block")
    assert any("velocity" in r for r in out["reasons"])


def test_duplicate_holds():
    e = ComplianceEngine()
    e.screen("Dup", 200.0, now=1000.0)
    out = e.screen("Dup", 200.0, now=1050.0)
    assert any("duplicate" in r for r in out["reasons"])
