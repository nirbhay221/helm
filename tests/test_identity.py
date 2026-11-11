"""An agent identity verifies when signed, fails when tampered or expired, and enforces
the capability it was issued."""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market.identity import issue_agent_identity, verify_agent_identity  # noqa: E402
from market.mandates import OwnerKey  # noqa: E402


def test_valid_identity_verifies():
    cred = issue_agent_identity(OwnerKey(), "agent-7", "ava", ["buy", "pool"])
    ok, payload, _ = verify_agent_identity(cred)
    assert ok is True and payload["agent_id"] == "agent-7" and "buy" in payload["capabilities"]


def test_tampered_identity_is_rejected():
    cred = issue_agent_identity(OwnerKey(), "agent-7", "ava", ["buy"])
    cred["payload"]["owner"] = "mallory"          # change the owner without re-signing
    ok, _, reason = verify_agent_identity(cred)
    assert ok is False and "signature" in reason


def test_capability_is_enforced():
    cred = issue_agent_identity(OwnerKey(), "agent-7", "ava", ["buy"])
    assert verify_agent_identity(cred, required_capability="buy")[0] is True
    ok, _, reason = verify_agent_identity(cred, required_capability="lend")
    assert ok is False and "capability" in reason


def test_expired_identity_is_rejected():
    cred = issue_agent_identity(OwnerKey(), "agent-7", "ava", ["buy"], ttl_seconds=1)
    time.sleep(1.2)
    ok, _, reason = verify_agent_identity(cred)
    assert ok is False and "expired" in reason
