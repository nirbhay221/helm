"""Graph-structural scoring flags a planted ring as a dense near-clique and scores it
above sparse structure."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market.graphfraud import analyze, ring_graph_features  # noqa: E402
from market.linkage import LinkageEngine  # noqa: E402
from market.marketplace import generate_marketplace  # noqa: E402


def test_planted_ring_is_a_dense_near_clique():
    m = generate_marketplace(120, 7)
    rings = LinkageEngine().infer(m)
    out = analyze(m, rings)
    assert out["count"] >= 1
    top = out["rings"][0]
    assert top["density"] >= 0.5                    # a coordinated ring is densely linked
    assert top["structural_risk"] >= 0.5
    assert 0.0 <= top["max_degree_ratio"] <= 1.0


def test_small_group_has_no_structural_claim():
    f = ring_graph_features([])
    assert f["members"] == 0 and f["near_clique"] is False and f["structural_risk"] == 0.0
