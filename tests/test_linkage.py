"""The linkage engine infers fraud rings from shared signals, not from labels."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market.linkage import LinkageEngine  # noqa: E402
from market.marketplace import generate_marketplace  # noqa: E402


def test_infers_the_two_planted_rings_by_signals():
    m = generate_marketplace(n_accounts=120, seed=7, n_serial_returners=3, n_bad_sellers=3)
    rings = LinkageEngine().infer(m)
    # the two coordinated rings (serial returners, bad sellers) are found
    assert len(rings) == 2
    # the detector was never told the cluster; it inferred from shared identifiers
    for r in rings:
        assert len(r.shared) >= 2            # linked on >= 2 strong identifiers
        assert r.risk >= 0.5 and r.action == "suspend_ring"
    found = {tuple(r.members) for r in rings}
    assert tuple(f"u{i:04d}" for i in range(3)) in found          # ring A = serial returners
    assert tuple(f"u{i:04d}" for i in range(3, 6)) in found       # ring B = bad sellers


def test_honest_accounts_are_not_grouped_into_rings():
    m = generate_marketplace(n_accounts=120, seed=7)
    ringed = {x for r in LinkageEngine().infer(m) for x in r.members}
    # only the 6 planted ring members are linked; honest users stay independent
    assert ringed == {f"u{i:04d}" for i in range(6)}


def test_links_a_rotated_device_ring_on_weaker_combined_signals():
    from market.marketplace import Account, Marketplace
    m = Marketplace()
    a = m.add_account(Account(id="x1", name="X1", country="US"))
    b = m.add_account(Account(id="x2", name="X2", country="US"))
    c = m.add_account(Account(id="x3", name="X3", country="US"))
    for acc, dev in ((a, "dev-A"), (b, "dev-B")):             # rotated device
        acc.payment_fp, acc.ip_prefix, acc.email_domain, acc.device_id = "card-Z", "ip-9.9", "ring.me", dev
    c.device_id, c.payment_fp, c.ip_prefix, c.email_domain = "dev-C", "card-C", "ip-1.1", "ring.me"
    rings = LinkageEngine().infer(m)
    members = {tuple(r.members) for r in rings}
    assert ("x1", "x2") in members                            # linked on payment+ip+email despite new device
    assert all("x3" not in r.members for r in rings)          # one weak shared signal is not enough


def test_cluster_of_maps_ring_members_to_an_inferred_id():
    m = generate_marketplace(n_accounts=120, seed=7)
    label = LinkageEngine().cluster_of(m)
    # the three serial returners share one inferred ring id
    ids = {label[f"u{i:04d}"] for i in range(3)}
    assert len(ids) == 1 and next(iter(ids)).startswith("ring-")
    # an honest account keeps its own id (not merged into any ring)
    assert label["u0100"] == "u0100"
