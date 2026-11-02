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
