# Phase 5 plan: offline evidence-retrieval evaluation on LoCoMo and LongMemEval (revised)

## Owner decisions (2026-11-03)
Datasets downloaded only after licence checks; originals and splits preserved; versions, sources and
checksums recorded; nothing large or restricted committed. Entirely offline, no paid API calls. Retrieval
measured separately from extraction and answer generation; keyword, structured and hybrid compared; Recall@k,
MRR, latency, ingestion time and memory footprint reported; temporal, multi-hop, contradiction and abstention
cases included; no official LoCoMo or LongMemEval scores claimed. An optional lightweight local embedding
model behind the provider interface, persisted in TypeDB, benchmarked, with offline mode intact without it.
Datasets and configuration frozen before tuning; development and held-out separate; first runs reported
honestly; where structure helps and where plain text retrieval wins both documented.

## Findings that shape the plan
- LoCoMo is CC BY-NC 4.0 (non-commercial research only) and LongMemEval is MIT: docs/datasets.md.
- Neither dataset has a development split; ours is fixed in `benchmarks/split.json` by id rule.
- Both are natural conversation. The offline rule extractor recovers little from them, so "structured" here
  means what TypeDB can do without good extraction: who said a turn (authorship), dated sessions and
  time windows, conversation/session scope, and whatever rule-extracted claims exist. It is expected to be
  weak on its own; the interesting question is whether it helps as a filter in the hybrid.
- Embeddings: `fastembed` (Apache-2.0, ONNX, no PyTorch) with BAAI/bge-small-en-v1.5 (MIT, 384 dimensions),
  as the optional `embeddings` extra. Vectors are stored in TypeDB (base64 float32, as ADR 0002), one
  `embedding` per observation and model. Without the extra, everything else still runs.

## Steps (each tested, committed, pushed)
1. Dataset manifest, split and frozen configuration (this commit), and a fetch script that verifies checksums.
2. Schema (core/0009): authorship of observations; persistent embeddings linked to observations.
3. Embedding provider (fastembed) behind `Embedder`; storage and exact search over TypeDB-stored vectors.
4. Evidence retrievers over a scope: keyword (existing), embedding, structured, hybrid (RRF).
5. Ingestion adapters for LoCoMo and LongMemEval (sessions as contexts, turns as observations with dates,
   speakers as authors), timed, with database size measured.
6. Development runs; any tuning committed; then each held-out set run once and reported as the first run.
7. Embedding benchmarks: generation speed, storage size, retrieval latency and scaling of exact search.
8. Report, ADR, and a Phase 6 proposal.
