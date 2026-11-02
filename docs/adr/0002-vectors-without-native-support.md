# ADR 0002: Embeddings without native TypeDB vectors (for now)

Status: proposed (Phase 0), 2026-11-02

## Context
The brief asks to use TypeDB's native vector functionality where supported, after verifying it.

Findings (2026-11-02):
- Installed: TypeDB CE **3.14.1** server, Python `typedb-driver` **3.14.0** (latest on PyPI).
- The live server rejects `value vector(3, "float32")`, `@index(hnsw:cosine)`, list-valued attributes
  and `cosine_similarity_search(...)` (`scripts/probe_vectors.py`; canary test in
  `tests/integration/test_smoke.py`).
- Native vectors exist only as an **open, unmerged pull request** (typedb/typedb#8014, retargeted to a
  feature branch on 2026-10-09, with changes requested), previewed in a TypeDB blog post as experimental.
  Reviewers list open problems: approximate (HNSW) misses, no index vacuum, crash-safety and restart
  bugs. It is not in the 3.14.0 or 3.14.1 release notes.

## Decision
- Store each embedding **in TypeDB** as a string attribute: little-endian float32, base64
  (`noodle_memory/typedb/embedding.py`), with the model name and dimension stored beside it.
- Compute similarity **exactly in Python** over vectors read from TypeDB, after structured filters have
  narrowed the candidates (source, context, type, time). No second vector store.
- Keep retrieval behind one function boundary so a native implementation can replace it when a released
  TypeDB version supports it; the canary test fails when the syntax starts being accepted.

## Consequences
- Exact search is O(n) per query: fine for the small-to-medium memories of Phases 1-5 (tens of
  thousands of chunks), not for millions. Benchmarks must report this honestly.
- Embeddings are opaque to TypeQL (no server-side similarity), so hybrid ranking happens in Python.
- An untested alternative: store components as `double` attributes in an index-ordered relation and
  compute dot products with TypeQL `reduce sum(...)`. Probably slow; worth one measurement in Phase 4.
