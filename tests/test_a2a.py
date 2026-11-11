"""Agent-to-agent buying is bounded by a cryptographically signed owner mandate."""
from __future__ import annotations

import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market.a2a import A2ADesk  # noqa: E402
from market.mandates import OwnerKey, issue_cart_mandate, issue_intent_mandate  # noqa: E402
from market.marketplace import Account, Listing, Marketplace  # noqa: E402
from paypal import Ledger, PayPalClient  # noqa: E402


def _desk():
    m = Marketplace()
    m.add_account(Account(id="seller", name="Seller", country="US"))
    m.list_item(Listing(id="cheap", seller="seller", title="print", price=40.0, category="prints"))
    m.list_item(Listing(id="mid", seller="seller", title="print2", price=80.0, category="prints"))
    m.list_item(Listing(id="beats", seller="seller", title="beat", price=30.0, category="beats"))
    return A2ADesk(m, PayPalClient(env={"DEMO_MODE": "1"}), Ledger())


def _intent(key, **kw):
    kw.setdefault("owner", "buyerX")
    kw.setdefault("max_total", 500.0)
    kw.setdefault("max_per_item", 100.0)
    kw.setdefault("allowed_categories", ("prints",))
    kw.setdefault("approval_threshold", 50.0)
    return issue_intent_mandate(key, **kw)


def test_signed_deal_within_the_mandate_settles_on_paypal():
    key = OwnerKey()
    d = _desk().buy(_intent(key), "cheap")
    assert d.status == "settled" and d.order_id and d.agreed == 40.0


def test_tampered_mandate_is_rejected():
    key = OwnerKey()
    cred = _intent(key)
    cred = copy.deepcopy(cred)
    cred["payload"]["max_per_item"] = 100000.0        # widen the cap without re-signing
    d = _desk().buy(cred, "mid")
    assert d.status == "rejected_unverified"          # the signature no longer matches


def test_category_outside_the_mandate_is_blocked():
    key = OwnerKey()
    d = _desk().buy(_intent(key), "beats")
    assert d.status == "blocked" and "category" in d.reason


def test_over_threshold_needs_a_signed_cart_mandate_agent_cannot_forge():
    key = OwnerKey()
    intent = _intent(key)
    desk = _desk()
    held = desk.buy(intent, "mid")                    # 80 > 50, no cart mandate
    assert held.status == "needs_owner_approval"
    # the owner signs a cart mandate for this exact deal
    cart = issue_cart_mandate(key, intent["payload"]["nonce"], "buyerX", "seller", "mid", 80.0)
    ok = desk.buy(intent, "mid", cart_credential=cart)
    assert ok.status == "settled"
    # a cart mandate signed by a DIFFERENT key (an impostor agent) is rejected
    forged = issue_cart_mandate(OwnerKey(), intent["payload"]["nonce"], "buyerX", "seller", "mid", 80.0)
    desk2 = _desk()
    assert desk2.buy(intent, "mid", cart_credential=forged).status == "needs_owner_approval"


def test_total_budget_cap_blocks_the_second_buy():
    key = OwnerKey()
    intent = _intent(key, max_total=100.0, approval_threshold=1e9)
    desk = _desk()
    assert desk.buy(intent, "cheap").status == "settled"
    assert desk.buy(intent, "mid").status == "blocked"


def test_credential_authority_binding_pins_the_owner_key():
    """Integrity alone is not authority: a credential self-signed with a different key
    verifies for integrity, but is rejected when the trusted owner key is pinned."""
    from market.mandates import OwnerKey, issue_intent_mandate, verify_credential
    owner = OwnerKey()
    cred = issue_intent_mandate(owner, "ava", max_total=500, max_per_item=100,
                                allowed_categories=["stocks"])
    owner_pub = cred["public_key"]
    # integrity ok, and authority ok when pinned to the real owner key
    assert verify_credential(cred)[0] is True
    assert verify_credential(cred, expected_public_key=owner_pub)[0] is True
    # an attacker self-signs a forged high-budget mandate with THEIR OWN key
    forged = issue_intent_mandate(OwnerKey(), "ava", max_total=1_000_000, max_per_item=1_000_000,
                                  allowed_categories=["stocks"])
    assert verify_credential(forged)[0] is True                       # passes integrity (self-consistent)
    ok, _, reason = verify_credential(forged, expected_public_key=owner_pub)
    assert ok is False and "owner key" in reason                      # rejected once authority is pinned
