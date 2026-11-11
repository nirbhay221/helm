"""The financial knowledge base retrieves the relevant principles for a query and
grounds them into a prompt block."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market.knowledge import KNOWLEDGE_BASE, ground, retrieve, topics  # noqa: E402


def test_retrieve_finds_the_relevant_principle():
    hits = retrieve("how much should we lend to a risky borrower", k=3)
    joined = " ".join(p.topic for p in hits)
    assert any(t in joined for t in ("expected loss", "large-exposure", "uncertainty", "pricing"))
    assert len(hits) <= 3


def test_retrieve_injection_query():
    hits = retrieve("the shopping agent reads an untrusted product listing", k=2)
    assert any("untrusted" in p.topic or "injection" in " ".join(p.tags) for p in hits)


def test_ground_returns_a_prompt_block():
    block = ground("platform revenue and viability", k=3)
    assert block.startswith("Relevant financial principles")
    assert block.count("\n- ") >= 1 or block.count("- ") >= 1


def test_base_is_nonempty_and_sourced():
    assert len(KNOWLEDGE_BASE) >= 10
    assert all(p.source and p.statement for p in KNOWLEDGE_BASE)
    assert len(topics()) == len(KNOWLEDGE_BASE)
