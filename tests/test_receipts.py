"""The receipt chain links each action to the previous hash and detects any later edit."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marketplace.receipts import ReceiptChain  # noqa: E402


def test_chain_is_intact_when_untampered():
    c = ReceiptChain()
    c.append("order", "A1", 100.0)
    c.append("capture", "A1", 100.0)
    c.append("payout", "P7", 40.0)
    v = c.verify()
    assert v["intact"] is True and v["length"] == 3
    # each receipt commits to the previous one
    assert c.receipts[1]["prev_hash"] == c.receipts[0]["hash"]


def test_tamper_is_detected():
    c = ReceiptChain()
    c.append("order", "A1", 100.0)
    c.append("capture", "A1", 100.0)
    c.append("payout", "P7", 40.0)
    c.receipts[1]["amount"] = 1000.0            # edit a settled amount after the fact
    v = c.verify()
    assert v["intact"] is False and v["broken_at"] == 1


def test_insertion_breaks_the_chain():
    c = ReceiptChain()
    c.append("order", "A1", 100.0)
    c.append("capture", "A1", 100.0)
    forged = dict(c.receipts[-1]); forged["seq"] = 1; forged["action"] = "capture"; forged["amount"] = 500.0
    c.receipts.insert(1, forged)                 # splice a forged receipt in
    assert c.verify()["intact"] is False
