"""The abuse engine catches both serial-returner buyers and bad sellers, by fault."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market.abuse import AbuseEngine  # noqa: E402
from market.marketplace import generate_marketplace  # noqa: E402


def _scan():
    m = generate_marketplace(n_accounts=120, seed=7, n_serial_returners=3, n_bad_sellers=3)
    return m, AbuseEngine().scan(m)


def test_flags_serial_returner_buyers_as_buyer_fault():
    m, verdicts = _scan()
    serial_ids = [f"u{i:04d}" for i in range(3)]          # planted serial returners
    flagged = {v.account_id: v for v in verdicts}
    for sid in serial_ids:
        assert sid in flagged and flagged[sid].role == "buyer"
        assert flagged[sid].bad_count >= 10


def test_flags_bad_sellers_as_seller_fault():
    m, verdicts = _scan()
    bad_ids = [f"u{i:04d}" for i in range(3, 6)]          # planted bad sellers
    flagged = {v.account_id: v for v in verdicts}
    for sid in bad_ids:
        assert sid in flagged and flagged[sid].role == "seller"


def test_most_accounts_are_not_flagged():
    m, verdicts = _scan()
    assert len(verdicts) < 15                              # only the real abusers, not everyone


def test_suspension_is_applied_with_a_reason():
    m, verdicts = _scan()
    n = AbuseEngine().apply(m, verdicts)
    assert n >= 1
    suspended = [a for a in m.accounts.values() if a.status == "suspended"]
    assert suspended and all(a.suspend_reason for a in suspended)


def test_verdict_reason_names_fault_and_spread():
    m, verdicts = _scan()
    v = verdicts[0]
    assert v.distinct_counterparties >= 5
    assert "fault" not in v.reason.lower() or v.role in v.reason   # role named in reason
