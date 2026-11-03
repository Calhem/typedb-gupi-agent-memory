# Revised roadmap (specialist direction)

Date: 2026-11-03. Direction: a specialist memory engine for agents working with complex, evolving and
potentially contradictory knowledge, built on TypeDB's typed relationships, temporal reasoning, provenance
and schema constraints. Not a general conversational-memory competitor. The advantage is a hypothesis to
test (capabilities.md), and each phase ends at a review gate.

| Phase | Content | Needs | Gate |
|---|---|---|---|
| 5 (done, under review) | LoCoMo / LongMemEval evidence retrieval; local embeddings in TypeDB | — | report reviewed; merge on approval |
| 6 | **Specialist evaluation first**: write the `projects` domain dataset (documents, gold claims, support labels, world state, questions; held-out part authored by the owner), the evaluation harness, and baselines 1-3 plus GUPI with oracle claims | offline only | dataset frozen before engine code; oracle vs text baselines reported |
| 7 | **Memory Formation Engine core** with deterministic and simulated providers: source documents, salience, support, attribution and modality, change analysis, schema-gap proposals, acceptance policy | offline; this design approved | formation metrics on the frozen dataset, labelled simulated |
| 8 | CronQuestions adapter (documented Wikidata subset; oracle question parsing stated) | offline; download approval | first-run results by question type |
| 9 | Real extraction and fair comparison: LLM extractor and support provider; same-model Graphiti baseline; same reader for all systems | LLM budget or local model decision; Graphiti needs Neo4j/FalkorDB for the baseline only | first-run held-out results, cost and latency |
| Later | AVeriTeC (support decision with oracle evidence); scaling (bulk ingestion; TypeDB native vectors when released); the brief's database-discovery track | as decided | — |

Changed from the original brief: the PostgreSQL discovery track (brief Phase 6) and the explorer UI move
after the specialist evaluation; LoCoMo/LongMemEval stay as independent checks, not targets.

## Decisions needed from the owner
1. Approve the Phase 5 report and merge.
2. Approve the two recommended benchmarks (CronQuestions; LongMemEval categories) and the CronQuestions
   download when Phase 8 starts.
3. Approve the formation-engine design (three decisions, change analysis, schema proposals) or amend it.
4. Agree the `projects` domain and offer to author part of the held-out questions.
5. When real extraction should be funded (budget) or which local model to use.
