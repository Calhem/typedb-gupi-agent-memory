# ADR 0008: Evidence retrieval, local embeddings in TypeDB, and the Phase 5 benchmark protocol

Status: accepted (Phase 5), 2026-11-03

## Embeddings
- Optional extra `embeddings`: fastembed 0.9.1 (Apache-2.0) with BAAI/bge-small-en-v1.5 (MIT; quantised
  ONNX, 384 dimensions, 64 MB, CPU), behind the existing `Embedder` interface (`FastEmbedder`).
- Stored in TypeDB (core/0009): one `embedding` per observation and model, a base64 float32 string linked
  by `embedding-of`; written in batches with `given` rows; idempotent per model. No other store.
- Search is exact cosine over the vectors in scope: `NumpyCosine` when NumPy is present (it comes with the
  extra), otherwise the pure-Python `ExactCosine`. Without the extra, every other path still works.

## Evidence retrievers (`gupi.evidence`), over a scope of contexts
keyword (BM25; TypeDB `contains` selects candidates in scope), embedding, structured (authorship,
mentions, names, time windows from the question, claim evidence; no text scoring; nothing without a named
entity), hybrid (RRF of keyword and embedding, filtered to structured candidates when there are any), and
hybrid-unfiltered (added before held-out runs as an ablation). Authorship (core/0009) records who said a turn.

## Benchmark protocol (as followed)
1. Licences checked at source; files pinned by version and SHA-256 (docs/datasets.md); data kept out of git.
2. Development/held-out split and retrieval configuration committed before any retrieval code
   (`benchmarks/split.json`, `benchmarks/config.json`).
3. Amendments, each committed before any held-out run and recorded in the config: rule extraction on LoCoMo
   only and image captions in LoCoMo turns (before any run); the hybrid-unfiltered ablation and a fixed
   64-question LongMemEval subset for embedding systems (after development runs; compute-only reason).
4. Each held-out configuration run once; results committed unchanged.
5. Reported as evidence retrieval only. These are not LoCoMo or LongMemEval scores.

## Consequences
Local embedding is the cost bottleneck (about 7-9 long turns/s on this laptop). Exact search over TypeDB-
stored vectors is fast for per-question scopes but reading vectors from TypeDB grows linearly with scope
(docs/evaluation/phase-5/embeddings.json). TypeDB native vectors (not in 3.14.1) remain the planned
replacement behind the same interface.
