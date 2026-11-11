"""A small embedded vector store for semantic retrieval, so agents retrieve by MEANING.

Helm's knowledge grounding matched keywords, which misses a principle phrased differently from the
query ("how much to lend someone whose pay swings" should still find the expected-loss rule even
though it shares no words). This adds real semantic retrieval: sentence embeddings (BAAI
bge-small-en-v1.5 via fastembed -- ONNX on CPU, no torch, so it runs on the box) plus cosine search
over a numpy matrix. It is the embedding layer the retrieval-augmented financial-agent literature
uses, kept embedded (no server) to match Helm's deployment.

If the embedding model is unavailable it falls back to a deterministic hashing embedder over word
and character n-grams -- lexical, not truly semantic, but stable and dependency-free -- so retrieval
degrades rather than breaks. The backend in use is always reported, honestly.
"""
from __future__ import annotations

import hashlib
import re

import numpy as np

_MODEL = "BAAI/bge-small-en-v1.5"
_HASH_DIM = 384                       # match the real model's dim so stores are interchangeable


class Embedder:
    """Embeds text to unit vectors. Prefers the ONNX sentence model; falls back to hashing."""

    def __init__(self):
        self._fe = None
        self._tried = False
        self.backend = "pending"

    def _ensure(self):
        if self._tried:
            return
        self._tried = True
        try:
            from fastembed import TextEmbedding
            self._fe = TextEmbedding(model_name=_MODEL)
            self.backend = "bge-small-en-v1.5"
        except Exception:
            self._fe = None
            self.backend = "hashing-fallback"

    def embed(self, texts) -> np.ndarray:
        self._ensure()
        texts = [str(t or "") for t in texts]
        if self._fe is not None:
            try:
                M = np.asarray(list(self._fe.embed(texts)), dtype=float)
                return _l2norm(M)
            except Exception:
                self._fe = None
                self.backend = "hashing-fallback"
        return _l2norm(np.asarray([_hash_embed(t) for t in texts], dtype=float))


def _l2norm(M: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(M, axis=1, keepdims=True)
    return M / np.clip(n, 1e-9, None)


def _hash_embed(text: str, dim: int = _HASH_DIM) -> np.ndarray:
    """Deterministic hashing embedder over word tokens and character 3-grams (md5, so it is stable
    across processes, unlike Python's salted hash). Lexical similarity, not semantic -- the fallback."""
    v = np.zeros(dim, dtype=float)
    s = (text or "").lower()
    toks = re.findall(r"\w+", s)
    grams = toks + [s[i:i + 3] for i in range(max(0, len(s) - 2))]
    for g in grams:
        h = int(hashlib.md5(g.encode("utf-8")).hexdigest(), 16) % dim
        v[h] += 1.0
    return v


class VectorStore:
    """An in-memory cosine-similarity index over embedded texts. Embedded: no server, no files."""

    def __init__(self, embedder: Embedder | None = None):
        self.embedder = embedder or Embedder()
        self.ids: list = []
        self.texts: list = []
        self.metas: list = []
        self.M: np.ndarray | None = None

    @property
    def backend(self) -> str:
        return self.embedder.backend

    def add(self, items) -> "VectorStore":
        """items: iterable of (id, text, meta). Embeds and appends to the index."""
        items = list(items)
        if not items:
            return self
        texts = [t for _i, t, _m in items]
        E = self.embedder.embed(texts)
        for (i, t, m) in items:
            self.ids.append(i)
            self.texts.append(t)
            self.metas.append(m)
        self.M = E if self.M is None else np.vstack([self.M, E])
        return self

    def scores(self, text: str) -> np.ndarray:
        """Cosine similarity of the query against every stored item, aligned with self.ids."""
        if self.M is None or not self.ids:
            return np.zeros(0)
        q = self.embedder.embed([text])[0]
        return self.M @ q

    def query(self, text: str, k: int = 4) -> list:
        """Return up to k nearest items as {id, text, meta, score}, most similar first."""
        sims = self.scores(text)
        if sims.size == 0:
            return []
        order = np.argsort(-sims)[:k]
        return [{"id": self.ids[j], "text": self.texts[j], "meta": self.metas[j],
                 "score": round(float(sims[j]), 4)} for j in order]
