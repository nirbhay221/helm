"""Graph-structure-aware scoring on inferred fraud rings.

The linkage engine finds candidate rings from shared identity signals. This adds the
graph lens the ring literature relies on: an organic group of unrelated people is
SPARSE (few of them link to each other), while a ring run by one actor is near a
CLIQUE (almost everyone links to everyone, because it is one person). So the intra-ring
edge density, and how concentrated the links are on a few hub nodes, are strong
structural signals on top of the per-pair model.

A full graph neural network would learn these features end to end, but it needs a deep
-learning runtime this box does not carry; the structural features here (density,
mean link probability, degree concentration, near-clique) are the same quantities a
GNN's first layers compute, done explicitly and cheaply with the engine's own link
model. Honest about what it is: graph-feature scoring, not a trained GNN.
"""
from __future__ import annotations

from itertools import combinations
from typing import List

from .linkage import _link_model, _pair_features


def ring_graph_features(accounts: List, link_threshold: float = 0.5) -> dict:
    """Compute structural features for one ring's member accounts: edge density,
    mean link probability, degree concentration, and whether it is a near-clique."""
    n = len(accounts)
    if n < 2:
        return {"members": n, "density": 0.0, "near_clique": False,
                "structural_risk": 0.0, "interpretation": "too small to score structurally"}
    model = _link_model()
    deg = [0] * n
    edges, probs = 0, []
    for i, j in combinations(range(n), 2):
        p = float(model.predict_proba(_pair_features(accounts[i], accounts[j])))
        probs.append(p)
        if p >= link_threshold:
            edges += 1
            deg[i] += 1
            deg[j] += 1
    possible = n * (n - 1) // 2
    density = round(edges / possible, 3) if possible else 0.0
    mean_prob = round(sum(probs) / len(probs), 3) if probs else 0.0
    max_degree_ratio = round(max(deg) / (n - 1), 3) if n > 1 else 0.0
    near_clique = density >= 0.8
    structural_risk = round(min(1.0, 0.6 * density + 0.4 * mean_prob), 3)
    interpretation = ("near-clique: almost every member links to every other, which organic "
                      "groups do not, so this is very likely one actor"
                      if near_clique else
                      "partially connected: weaker structural evidence of a single actor")
    return {"members": n, "edges": edges, "possible_edges": possible, "density": density,
            "mean_link_prob": mean_prob, "max_degree_ratio": max_degree_ratio,
            "near_clique": near_clique, "structural_risk": structural_risk,
            "interpretation": interpretation}


def analyze(marketplace, rings) -> dict:
    """Score every inferred ring structurally. Returns one row per ring, highest
    structural risk first."""
    rows = []
    for r in rings:
        accs = [marketplace.accounts[i] for i in r.members if i in marketplace.accounts]
        feats = ring_graph_features(accs)
        feats["ring_members"] = list(r.members)
        feats["bad_rate"] = getattr(r, "bad_rate", 0.0)
        rows.append(feats)
    rows.sort(key=lambda x: x["structural_risk"], reverse=True)
    return {"rings": rows, "count": len(rows)}
