"""x402 returns a 402 challenge, settles a correct payment, and refuses a tampered amount."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market.x402 import requirements, settle  # noqa: E402
from paypal import Ledger, PayPalClient  # noqa: E402


def _demo():
    return PayPalClient(env={"DEMO_MODE": "1"}), Ledger(":memory:")


def test_requirements_shape():
    reqs, ch = requirements("premium-signal", 0.25)
    assert reqs["x402Version"] == 1 and reqs["accepts"]
    opt = reqs["accepts"][0]
    assert opt["scheme"] == "exact" and opt["maxAmountRequired"] == 0.25 and opt["payTo"]
    assert ch["payload"]["type"] == "IntentToken"


def test_correct_payment_is_granted():
    client, ledger = _demo()
    reqs, ch = requirements("premium-signal", 0.25)
    out = settle(ch, "premium-signal", 0.25, client, ledger)
    assert out["granted"] is True and out["status"] == 200
    assert out["resource"] == "premium-signal"


def test_tampered_amount_is_refused():
    client, ledger = _demo()
    reqs, ch = requirements("premium-signal", 0.25)
    out = settle(ch, "premium-signal", 2.50, client, ledger)   # pay a different amount than agreed
    assert out["granted"] is False and out["status"] == 402
