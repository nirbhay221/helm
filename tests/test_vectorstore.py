"""The vector store retrieves by meaning, and the knowledge grounding is hybrid and robust.

These do not require the embedding model: the store falls back to a deterministic hashing embedder,
and the hybrid retriever blends it with keyword overlap, so the tests pass with or without fastembed
installed. We assert vectors are unit length, the fallback is deterministic, the store finds the
right item, and the knowledge base returns the correct domain principle for paraphrased queries.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from market import knowledge as K
from market.vectorstore import Embedder, VectorStore, _hash_embed


def test_embeddings_are_unit_vectors():
    E = Embedder()
    M = E.embed(["expected loss", "the weather on tuesday"])
    norms = np.linalg.norm(M, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-6)
    assert E.backend in ("bge-small-en-v1.5", "hashing-fallback")


def test_hashing_fallback_is_deterministic():
    a = _hash_embed("expected loss equals pd times lgd")
    b = _hash_embed("expected loss equals pd times lgd")
    assert np.array_equal(a, b)                       # stable across calls (md5, not salted hash)
    assert not np.array_equal(a, _hash_embed("something else entirely"))


def test_store_retrieves_the_relevant_item():
    s = VectorStore().add([
        ("lend", "how much to lend a risky borrower given default probability", {}),
        ("weather", "it was sunny and warm on tuesday afternoon", {}),
        ("pay", "release the creator payout once the chargeback window closes", {}),
    ])
    top = s.query("what is the default risk of a borrower", k=1)
    assert top and top[0]["id"] == "lend"             # nearest by meaning/lexical overlap


def test_knowledge_finds_the_right_domain_principle():
    # a paraphrase sharing few keywords with the principle statement
    tops = [p.topic for p in K.retrieve("stop one borrower from sinking the whole fund", k=3)]
    assert "large-exposure limit" in tops
    tops2 = [p.topic for p in K.retrieve("an agent tried to pay more than the owner approved", k=3)]
    assert "spend authority" in tops2


def test_retrieval_backend_is_reported():
    assert K.retrieval_backend() in ("bge-small-en-v1.5", "hashing-fallback", "keyword")


def test_retrieve_never_returns_empty():
    assert len(K.retrieve("anything at all", k=4)) >= 1
    assert len(K.retrieve("", k=4)) >= 1
