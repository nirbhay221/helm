"""Property-based tests: the money invariants hold for EVERY input, not just the examples.

Each test states an invariant a bank's payments team would demand and lets Hypothesis
generate adversarial inputs (negative, huge, NaN and infinite amounts, unknown payees,
replayed tokens, tampered records, split payments) to try to break it. Example tests show
a feature works; these show the guardrails cannot be argued or fuzzed past.
"""
from __future__ import annotations

import copy
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from market.a2a import check_deal
from market.compliance import STRUCTURING_THRESHOLD, ComplianceEngine
from market.escrow import Criterion, Escrow
from market.guard import issue_intent_token, verify_intent_token
from market.mandates import OwnerKey, issue_intent_mandate
from marketplace.advance import AdvanceEngine, SafetyFund
from marketplace.receipts import ReceiptChain
from marketplace.recon import reconcile
from paypal import Ledger, PayPalClient

FAST = settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
money = st.floats(min_value=0.01, max_value=50_000, allow_nan=False, allow_infinity=False)
weird = st.one_of(money, st.floats(allow_nan=True, allow_infinity=True), st.just(-5.0),
                  st.just(0.0), st.text(max_size=5))

_KEY = OwnerKey()                         # one signing key; ES256 keygen is the slow part


# --- spend authority -----------------------------------------------------------------------
@FAST
@given(max_total=st.floats(10, 5000), per_item=st.floats(1, 2000),
       prices=st.lists(money, min_size=1, max_size=30))
def test_an_agent_can_never_spend_past_its_signed_mandate(max_total, per_item, prices):
    """Whatever deals an agent proposes, in any order, spend stays inside the signed budget."""
    cred = issue_intent_mandate(_KEY, "owner", max_total=max_total, max_per_item=per_item)
    spent = 0.0
    for p in prices:
        d = check_deal(cred, "goods", p, spent=spent)
        if d["fits"] and not d["needs_approval"]:
            assert p <= per_item + 1e-6
            spent += p
    assert spent <= max_total + 1e-6


@FAST
@given(max_total=st.floats(10, 5000), raised=st.floats(5001, 1e7))
def test_a_tampered_mandate_never_verifies(max_total, raised):
    """Raising the budget after the owner signed breaks the signature."""
    cred = issue_intent_mandate(_KEY, "owner", max_total=max_total, max_per_item=max_total)
    forged = copy.deepcopy(cred)
    forged["payload"]["max_total"] = raised
    out = check_deal(forged, "goods", min(raised, 1e6), spent=0.0)
    assert out["verified"] is False and out["fits"] is False


@FAST
@given(amount=money, charged=money, item=st.text(min_size=1, max_size=20))
def test_an_intent_token_only_pays_exactly_what_was_reviewed_and_only_once(amount, charged, item):
    tok = issue_intent_token(item, amount, "goods")
    if round(charged, 2) != round(amount, 2):
        ok, _ = verify_intent_token(tok, item, charged, "goods")
        assert not ok                                  # a different amount is refused
    ok1, _ = verify_intent_token(tok, item, amount, "goods")
    ok2, _ = verify_intent_token(tok, item, amount, "goods")
    assert ok1 and not ok2                             # single use: a replay is refused


# --- advances against the safety fund ------------------------------------------------------
@FAST
@given(fund=st.floats(0, 1e6), earnings=st.floats(0, 1e6),
       history=st.one_of(st.none(), st.lists(st.floats(0, 5000), min_size=1, max_size=24)),
       ask=st.floats(0.01, 2e6))
def test_an_advance_never_breaks_the_lending_caps(fund, earnings, history, ask):
    """No offer exceeds 80% of proven earnings, 20% of the fund per borrower, or what the fund
    can cover at its target loss coverage; asking for more is rejected and moves no money."""
    eng, f = AdvanceEngine(), SafetyFund(fund)
    o = eng.offer("c", earnings, f, history)
    assert o.max_amount <= eng.advance_rate * earnings + 0.01
    assert o.max_amount <= eng.concentration * fund + 0.01
    assert o.max_amount <= eng.portfolio_capacity(f) + 0.01
    before = f.balance
    r = eng.take("c", ask, earnings, f, approved=True, earnings_history=history)
    if ask > o.max_amount + 1e-6:
        assert r["status"] == "rejected" and f.balance == before
    else:
        assert r["status"] in ("advanced", "rejected")
        if r["status"] == "advanced":
            assert math.isclose(f.balance, round(before - r["amount"], 2), abs_tol=0.011)


@FAST
@given(principal=st.floats(1, 10_000), payouts=st.lists(st.floats(0, 5000), max_size=40))
def test_repayment_conserves_money_and_never_over_collects(principal, payouts):
    """Every payout splits exactly into withheld + net, the fund receives exactly what was
    withheld, and the creator never repays more than they owe."""
    eng, f = AdvanceEngine(), SafetyFund(1e9)
    r = eng.take("c", principal, principal * 2, f, approved=True)
    assume(r["status"] == "advanced")
    owed, collected, fund0 = r["outstanding"], 0.0, f.balance
    for p in payouts:
        out = eng.repay_from_payout("c", p, f)
        assert math.isclose(out["withheld"] + out["net"], p, abs_tol=0.011)
        assert out["withheld"] >= 0 and out["net"] >= -0.01
        collected += out["withheld"]
    assert collected <= owed + 0.01
    assert math.isclose(f.balance - fund0, collected, abs_tol=0.01 * (len(payouts) + 1))


# --- outbound screening ----------------------------------------------------------------------
@FAST
@given(parts=st.lists(st.floats(1, STRUCTURING_THRESHOLD - 1), min_size=2, max_size=25))
def test_structuring_can_never_slip_a_reportable_total_through(parts):
    """Splitting money to one payee into sub-threshold pieces inside the window: the payments
    the screen lets proceed (allow or hold) never add up to the reporting threshold."""
    eng, t0, proceeded = ComplianceEngine(), 1_000_000.0, 0.0
    for i, p in enumerate(parts):
        d = eng.screen("payee-x", p, now=t0 + i)
        if d["decision"] != "block":
            proceeded += round(p, 2)
    assert proceeded < STRUCTURING_THRESHOLD + 1e-6


@FAST
@given(amount=money)
def test_a_sanctioned_payee_is_always_blocked(amount):
    assert ComplianceEngine().screen("Sanctioned Entity", amount)["decision"] == "block"


# --- tamper evidence and reconciliation ------------------------------------------------------
@FAST
@given(amounts=st.lists(money, min_size=1, max_size=15), data=st.data())
def test_any_edit_to_any_receipt_is_detected_at_or_before_it(amounts, data):
    ch = ReceiptChain()
    for i, a in enumerate(amounts):
        ch.append("payout", f"ref-{i}", a)
    assert ch.verify()["intact"]
    i = data.draw(st.integers(0, len(amounts) - 1))
    field = data.draw(st.sampled_from(["amount", "ref", "action"]))
    ch.receipts[i][field] = {"amount": ch.receipts[i]["amount"] + 0.01, "ref": "evil",
                             "action": "refund"}[field]
    v = ch.verify()
    assert not v["intact"] and v["broken_at"] <= i


@FAST
@given(rows=st.lists(st.tuples(st.text(min_size=1, max_size=8), money), min_size=1, max_size=20,
                     unique_by=lambda r: r[0]), data=st.data())
def test_reconciliation_never_reports_done_when_the_processor_disagrees(rows, data):
    exp = [{"ref": r, "amount": a} for r, a in rows]
    assert reconcile(exp, copy.deepcopy(exp))["clean"]
    k = data.draw(st.integers(0, len(exp) - 1))
    kind = data.draw(st.sampled_from(["drop", "change", "duplicate", "extra"]))
    act = copy.deepcopy(exp)
    if kind == "drop":
        act.pop(k)
    elif kind == "change":
        act[k]["amount"] = round(act[k]["amount"] + 1.0, 2)
    elif kind == "duplicate":
        act.append(dict(act[k]))
    else:
        act.append({"ref": "never-initiated-" + exp[k]["ref"], "amount": 5.0})
    assert not reconcile(exp, act)["clean"]


# --- pay-on-proof escrow ------------------------------------------------------------------------
crit = st.builds(Criterion, key=st.sampled_from(["delivered", "tests", "photo"]),
                 predicate=st.sampled_from(["truthy", "equals", "at_least"]),
                 expected=st.one_of(st.integers(0, 20), st.booleans(), st.none()))
delivery = st.dictionaries(st.sampled_from(["delivered", "tests", "photo", "extra"]),
                           st.one_of(st.integers(-5, 30), st.booleans(), st.none(), st.text(max_size=3)))


@settings(max_examples=120, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(criteria=st.lists(crit, min_size=1, max_size=4), dl=delivery, amount=money)
def test_escrow_releases_exactly_when_every_criterion_holds(criteria, dl, amount):
    """Money is captured if and only if the delivery satisfies every criterion fixed at funding;
    criteria an empty delivery could satisfy are refused before any money is held."""
    client, led = PayPalClient(env={}), Ledger(":memory:")
    e = Escrow("buyer", "seller", amount, list(criteria))
    funded = e.fund(client, led)
    if all(c.check({}) for c in criteria):
        assert funded["status"] == "rejected"
        assert not any(m["kind"] in ("authorize", "capture") for m in led.movements())
        return
    assert funded["status"] == "held"
    out = e.settle(dl, client, led)
    should = all(c.check(dl) for c in criteria)
    assert out["status"] == ("released" if should else "refunded")
    captures = [m for m in led.movements() if m["kind"] == "capture"]
    assert len(captures) == (1 if should else 0)
    again = e.settle(dl, client, led)                  # settling twice never moves money twice
    assert again["status"] == out["status"]
    assert len([m for m in led.movements() if m["kind"] == "capture"]) == len(captures)


# --- the operator's dispose step -------------------------------------------------------------
def _operator_tools():
    from tests.test_operator_graph import _build
    return _build()[1]


alloc_item = st.fixed_dictionaries({"creator": st.sampled_from(["Ava", "Ben", "Cy", "Mallory", ""]),
                                    "amount": weird})


@settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(allocs=st.lists(alloc_item, max_size=8), mult=st.floats(0.0, 5.0))
def test_whatever_the_agents_propose_the_payout_stays_inside_the_safe_release(allocs, mult):
    """The agents' proposal is untrusted input: unknown payees, NaN, negative, infinite and
    oversized amounts. The paid total never exceeds the solver's safe release, no creator is
    paid more than they are owed, and no payee outside the roster is ever paid."""
    tools = _operator_tools()
    owed = {n: tools.led.total_unpaid(n) for n in tools.creators}
    cap = tools.size_safe_release(mult)["safe_release_total"]
    out = tools.pay_creators(allocs, approved=True)
    assert out["paid_total"] <= cap + 1e-6
    for p in out["paid"]:
        assert p["creator"] in tools.creators
        assert p["amount"] <= owed[p["creator"]] + 1e-6
        assert p["amount"] > 0 and math.isfinite(p["amount"])


@settings(max_examples=300, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(amounts=st.lists(st.floats(50, 5000), min_size=2, max_size=3), mult=st.floats(1.0, 3.0))
def test_an_oversized_proposal_is_scaled_to_never_exceed_the_cap_by_even_a_cent(amounts, mult):
    """Regression for a bug this suite found: scaling an oversized proposal and rounding each
    share to the NEAREST cent let the total overshoot the safe release by up to 2 cents."""
    tools = _operator_tools()
    for n in tools.creators:                       # owe enough that the cap, not the debt, binds
        tools.led.accrue(n, 10_000.0, -9)
    cap = tools.size_safe_release(mult)["safe_release_total"]
    names = list(tools.creators)
    out = tools.pay_creators([{"creator": names[i], "amount": a} for i, a in enumerate(amounts)],
                             approved=True)
    assert out["paid_total"] <= cap + 1e-9
