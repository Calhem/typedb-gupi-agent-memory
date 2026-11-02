"""Embeddings stored in TypeDB without native vector support (see docs/adr/0002).

TypeDB 3.14.1 has no vector value type, so a vector is stored as a string attribute holding
little-endian float32 values in base64. Similarity is computed exactly in Python over vectors read
back from TypeDB; there is no second vector store.
"""

import base64
import math
import struct


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
