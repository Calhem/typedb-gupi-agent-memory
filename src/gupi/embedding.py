"""Embeddings behind replaceable interfaces (docs/adr/0002-vectors-without-native-support.md).

- `Embedder` turns text into vectors (an LLM provider, a local model, or a deterministic test fixture).
- `SimilaritySearch` ranks candidate vectors against a query vector.

TypeDB 3.14.1 has no vector type, so the current `SimilaritySearch` is `ExactCosine`: vectors are stored in
TypeDB as base64 float32 strings (`encode`/`decode`) and compared exactly in Python. When a released TypeDB
supports native vector search, a TypeDB-backed `SimilaritySearch` replaces it without changing callers.
Deliberately unoptimised: correctness first.
"""

import base64
import math
import struct
from typing import Iterable, Protocol, Sequence


class Embedder(Protocol):
    model: str
    dimension: int

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


class SimilaritySearch(Protocol):
    def search(self, query: Sequence[float], candidates: Iterable[tuple[str, Sequence[float]]],
               k: int) -> list[tuple[str, float]]: ...


def encode(vector):
    return base64.b64encode(struct.pack(f"<{len(vector)}f", *vector)).decode("ascii")


def decode(text):
    raw = base64.b64decode(text)
    return list(struct.unpack(f"<{len(raw) // 4}f", raw))


def cosine(a, b):
    if len(a) != len(b):
        raise ValueError(f"dimension mismatch: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    if norm == 0:
        raise ValueError("zero-length vector has no direction")
    return dot / norm


class ExactCosine:
    """Exact cosine similarity over every candidate: O(n) per query."""

    def search(self, query, candidates, k):
        scored = [(cid, cosine(query, vector)) for cid, vector in candidates]
        scored.sort(key=lambda s: (-s[1], s[0]))  # ties broken by id, so results are deterministic
        return scored[:k]


class FastEmbedder:
    """A local embedding model through fastembed (ONNX, CPU, no PyTorch). Optional: `uv sync --extra embeddings`.

    Model files are cached in `cache_dir` (default .data/models, git-ignored). Nothing leaves the machine
    after the one-time model download.
    """

    def __init__(self, model="BAAI/bge-small-en-v1.5", cache_dir=".data/models", batch_size=64):
        try:
            from fastembed import TextEmbedding
        except ImportError as e:
            raise RuntimeError("local embeddings need the optional dependency: uv sync --extra embeddings") from e
        self.model = model
        self._impl = TextEmbedding(model, cache_dir=cache_dir)
        self.dimension = len(next(iter(self._impl.embed(["dimension probe"]))))
        self.batch_size = batch_size

    def embed(self, texts):
        return [list(map(float, v)) for v in self._impl.embed(list(texts), batch_size=self.batch_size)]


class NumpyCosine:
    """Exact cosine similarity with NumPy (installed with the embeddings extra). Same results as ExactCosine."""

    def search(self, query, candidates, k):
        import numpy as np
        candidates = list(candidates)
        if not candidates:
            return []
        ids = [cid for cid, _ in candidates]
        m = np.asarray([v for _, v in candidates], dtype=np.float32)
        q = np.asarray(query, dtype=np.float32)
        norms = np.linalg.norm(m, axis=1) * np.linalg.norm(q)
        if not norms.all():
            raise ValueError("zero-length vector has no direction")
        scores = (m @ q) / norms
        order = sorted(range(len(ids)), key=lambda i: (-float(scores[i]), ids[i]))[:k]
        return [(ids[i], float(scores[i])) for i in order]
