# ADR 0002: Embeddings without native TypeDB vectors (for now)

Status: accepted, 2026-11-02

## Context
The brief asks to use TypeDB's native vector functionality where supported, after verifying it.

Findings (2026-11-02):
- Installed: TypeDB CE **3.14.1** server, Python `typedb-driver` **3.14.0** (latest on PyPI).
- The live server rejects `value vector(3, "float32")`, `@index(hnsw:cosine)`, list-valued attributes
  and `cosine_similarity_search(...)` (`scripts/probe_vectors.py`; canary test in
  `tests/integration/test_smoke.py`).
- Native vectors exist only as an **open, unmerged pull request** (typedb/typedb#8014, retargeted to a
  feature branch on 2026-10-09, with changes requested), previewed in a TypeDB blog post as experimental.
  It is not in the 3.14.0 or 3.14.1 release notes.

## Decision
- Embeddings live **in TypeDB** as string attributes: little-endian float32, base64 (`gupi.embedding`),
  with the model name and dimension beside them. No second vector store.
- Two replaceable interfaces in `gupi.embedding`: `Embedder` (text -> vectors) and `SimilaritySearch`
  (rank candidates). The current `SimilaritySearch` is `ExactCosine`, deliberately unoptimised.
- When a released TypeDB supports native vectors (the canary test fails), add a TypeDB-backed
  `SimilaritySearch`; callers do not change.

## Consequences
- Exact search is O(n) per query: fine for tens of thousands of items, not millions. Benchmarks must
  say so. Structured filters should narrow candidates first.
- Embedding storage in the ontology is Phase 4 work; Phase 1 only fixes the interfaces.
