# Phase 5 report: offline evidence-retrieval evaluation and local embeddings

Date: 2026-11-03. Branch: `feature/phase-5-evaluation` (from `main` at `37afa43`, where Phase 4 was merged
after verification). TypeDB CE 3.14.1; typedb-driver 3.14.0; Python 3.13. Offline, no paid API calls.
**Not merged; awaiting review.**

## Phase 4 merge
Diff reviewed (9 commits, 34 files), 160 tests passing, extraction benchmarks byte-for-byte unchanged, no
secrets, unintended files or possible conflicts; merged with `--no-ff`; remote `main` verified at `37afa43`.

## Owner requirements
| Requirement | Delivered |
|---|---|
| Licences checked before download | LoCoMo CC BY-NC 4.0 (non-commercial research), LongMemEval MIT; docs/datasets.md |
| Originals, splits, versions, sources, checksums | pinned versions, SHA-256 verified (`scripts/fetch_datasets.py`); files unchanged in git-ignored `.data/`; our dev/held-out split by id rule |
| No large or restricted content committed | only ids, checksums, configuration and aggregate results |
| Offline, no paid calls | yes; Claude never called |
| Reproducible ingestion adapters | `gupi.benchmarks.locomo`, `gupi.benchmarks.longmemeval`; `python -m gupi.benchmarks` |
| Retrieval separate from extraction and answers | evidence retrieval only; no answer generation; not official scores |
| Keyword, structured, hybrid compared (and embedding) | five systems, including a pre-registered hybrid-unfiltered ablation |
| Recall@k, MRR, latency, ingestion, footprint | per system, unit and category; database size and peak memory |
| Temporal, multi-hop, contradiction, abstention cases | LoCoMo temporal / multi-hop / adversarial; LongMemEval temporal-reasoning / multi-session / knowledge-update / abstention |
| Optional local embeddings behind the interface, stored in TypeDB | fastembed + bge-small-en-v1.5; `embedding` entities in TypeDB; fully functional without the extra |
| Embedding benchmarks | generation, storage, write and search scaling to 50,000 vectors |
| Frozen before tuning; dev and held-out separate; first runs honest | config and split committed before code; amendments committed before held-out runs; one held-out run each |

## Results (held-out, first run; details in docs/evaluation/phase-5/README.md)
- LoCoMo turn R@5: keyword **0.502**, hybrid-unfiltered 0.469, hybrid 0.428, embedding 0.363, structured 0.011.
- LongMemEval (447 questions) keyword: session R@5 0.890, turn R@5 0.683; structured 0.
- LongMemEval subset (64): session R@5 embedding **0.933**, hybrid 0.923, keyword 0.836; turn R@5 hybrid
  **0.685**, keyword 0.653, embedding 0.618; structured 0.
- **Structure helped** only on LoCoMo multi-hop questions (hybrid 0.200 vs 0.154 keyword) and **hurt** on
  adversarial questions (0.272 vs 0.565 unfiltered), where the question names the wrong speaker.
- **Text retrieval did better** on these conversational benchmarks overall: keyword on LoCoMo, embedding
  and hybrid on LongMemEval. Causes in the evaluation README: no extracted claims from natural chat, no
  entity handle in first-person questions, structure that narrows but does not rank.

## Performance
Ingestion 113-199 turns/s; local embedding 56 short / 9 long turns per second (the bottleneck: about an hour
for 32,000 LongMemEval turns); LongMemEval held-out database 815 MB for 220,178 turns; peak Python memory
2.5 GB (parsing the 277 MB JSON); exact vector search over 50,000 TypeDB-stored vectors 5.3 s, dominated by
reading them from TypeDB.

## Tests
`uv run pytest -q`: **171 passed** against the live server (162 passed, 1 skipped, with no optional extras
installed). New: vectors and authorship (2), evidence retrievers (3), benchmark helpers (5), NumPy cosine (1).

## Decisions
ADR 0008 (new): local embeddings in TypeDB, evidence retrievers, and the benchmark protocol.

## Limitations
- Retrieval-only; no answers, so no comparison with published LoCoMo or LongMemEval systems is possible.
- The structured retriever had almost no structure to use (no real extraction offline); this tests what
  TypeDB adds without good extraction, not GUPI's full design.
- LongMemEval embedding systems ran on a 64-question subset (compute); keyword ran on all 447.
- One machine, one run; latency figures are indicative.
- LoCoMo's non-commercial licence: GUPI's use is treated as research; any commercial use needs review.
- During development an embedding run stalled under memory pressure (the machine was swapping while a
  second process parsed the 277 MB file); it was stopped and repeated alone. No held-out run was affected.
