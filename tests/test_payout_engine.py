"""The five-part payout engine: Mete, Bulwark, Clearwright, Tollgate, Keystone."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from arms.payout_engine import (  # noqa: E402
    Contribution, MoneyEdge, Party,
    check_plan, execute_batch, harden_split, shapley_split, withhold,
)
from paypal import Ledger, PayPalClient  # noqa: E402


def _client():
    return PayPalClient(env={"DEMO_MODE": "1"})


# --- Mete -------------------------------------------------------------------
def test_shapley_is_efficient_and_symmetric():
    # A and B touch the same single conversion equally; C touches one alone
    res = shapley_split(300.0, [
        Contribution("A", {"c1"}),
        Contribution("B", {"c1"}),
        Contribution("C", {"c2"}),
    ])
    assert abs(sum(res.shares.values()) - 300.0) < 0.05        # efficient
    assert abs(res.shares["A"] - res.shares["B"]) < 0.05       # symmetric
    assert res.shares["C"] > res.shares["A"]                   # sole credit worth more


def test_shapley_zero_for_no_contribution():
    res = shapley_split(100.0, [Contribution("A", {"c1"}), Contribution("Z", set())])
    assert res.shares["Z"] == 0.0
    assert abs(res.shares["A"] - 100.0) < 0.05


# --- Bulwark ----------------------------------------------------------------
def test_bulwark_defeats_the_cheat():
    honest = [Party("A", 400), Party("B", 300), Party("C", 150)]
    cheater = Party("Z", 500, cluster="Z", honest=False)
    res = harden_split(1000.0, honest, cheater, cap_fraction=0.4)
    assert res.naive_cheater_take > res.honest_cheater_share + 0.01   # cheat paid, before
    assert res.hardened_cheater_take <= res.honest_cheater_share + 0.01  # not, after
    assert res.defeated is True
    assert res.hardening_applied                                      # something was switched on


# --- Clearwright ------------------------------------------------------------
def test_clearwright_blocks_payroll():
    res = check_plan([MoneyEdge("operator", "worker@ex.com", 500, "PAYROLL", "payouts")])
    assert res.ok is False
    assert any("PAYROLL" in v.reason for v in res.violations)


def test_clearwright_blocks_pooling_and_third_party_transfer():
    res = check_plan([MoneyEdge("customer", "operator", 100, "REWARD", "payouts")])
    assert res.ok is False


def test_clearwright_passes_legal_plan():
    res = check_plan([
        MoneyEdge("operator", "a@ex.com", 50, "COMMISSION", "payouts"),
        MoneyEdge("operator", "supplier@ex.com", 200, "SUPPLIER_GOODS", "orders"),
    ])
    assert res.ok is True


# --- Tollgate ---------------------------------------------------------------
def test_tollgate_withholds_cross_border_and_not_domestic():
    res = withhold([
        {"recipient": "us@ex.com", "amount": 100, "country": "US"},
        {"recipient": "in@ex.com", "amount": 100, "country": "IN"},
    ], home_country="US")
    by = {L.recipient: L for L in res.lines}
    assert by["us@ex.com"].withheld == 0.0
    assert by["in@ex.com"].withheld == 15.0
    assert res.total_net == 185.0


# --- Keystone ---------------------------------------------------------------
def test_keystone_conserves_on_partial_failure():
    c, led = _client(), Ledger()
    recipients = [
        {"email": "a@ex.com", "amount": 100},
        {"email": "b@ex.com", "amount": 50},
        {"email": "c@ex.com", "amount": 25},
    ]
    res = execute_batch(c, led, recipients, "ks-1", "COMMISSION",
                        fail_items={"b@ex.com"}, approved=True)
    assert res.status == "partial"
    assert res.conserved is True
    assert abs(res.intended_total - (res.paid_total + res.unpaid_total)) < 0.01
    assert res.unpaid_total == 50.0


def test_keystone_settles_fully_when_all_succeed():
    c, led = _client(), Ledger()
    res = execute_batch(c, led, [{"email": "a@ex.com", "amount": 40}],
                        "ks-2", "REWARD", approved=True)
    assert res.status == "settled"
    assert res.paid_total == 40.0 and res.unpaid_total == 0.0
