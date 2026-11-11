"""Reconciliation matches expected settlements to the processor's record and flags every
discrepancy type."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marketplace.recon import reconcile  # noqa: E402


def test_clean_reconciliation():
    exp = [{"ref": "A1", "amount": 100.0}, {"ref": "A2", "amount": 50.0}]
    act = [{"ref": "A1", "amount": 100.0, "status": "captured"},
           {"ref": "A2", "amount": 50.0, "status": "captured"}]
    out = reconcile(exp, act)
    assert out["clean"] is True and out["matched_count"] == 2 and out["matched_value"] == 150.0


def test_missing_and_mismatch_and_unexpected_and_duplicate():
    exp = [{"ref": "A1", "amount": 100.0}, {"ref": "A2", "amount": 50.0}, {"ref": "A3", "amount": 20.0}]
    act = [{"ref": "A1", "amount": 90.0},      # amount mismatch
           {"ref": "A2", "amount": 50.0}, {"ref": "A2", "amount": 50.0},  # duplicate
           {"ref": "Z9", "amount": 5.0}]       # unexpected; A3 missing
    out = reconcile(exp, act)
    types = {d["type"] for d in out["discrepancies"]}
    assert {"missing", "amount_mismatch", "unexpected", "duplicate"} <= types
    assert out["clean"] is False
    missing = [d for d in out["discrepancies"] if d["type"] == "missing"][0]
    assert missing["ref"] == "A3"
