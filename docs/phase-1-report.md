# Phase 1 report: core ontology and persistence

Date: 2026-11-02. Branch: `feature/phase-1-core`. Server: TypeDB CE 3.14.1; driver typedb-driver 3.14.0;
Python 3.13.

## Gate
"Ingest and retrieve structured evidence with source trace; reruns do not duplicate it." **Met**: see
`tests/integration/test_ingest.py` and `test_claims.py`.

## Pre-Phase-1 amendments
1. **ADR-0001 reviewed against four scenarios** (ADR 0001 has the table). Change: a claim is now one
   attestation (`fact` renamed `claim`), with `proposition-key` grouping claims about the same thing and
   `alternatives` for competing readings of one observation. Each claim and its provenance are
   retrievable on their own (tested).
2. **Re-acceptance after rejection fixed.** Reviews are historical events; the latest review recorded by
   t decides. TypeQL `believed_at` and Python `status_at` agree at every point of a
   hypothesis -> accepted -> rejected -> accepted history (tested), with conservative tie-breaking.
3. **False / unknown / not-yet-known kept apart**, plus CONTESTED for disagreeing believed claims.
   Tested with month and year precision, unknown starts, retrospective start-date corrections and
   late retractions.
4. **Embeddings** sit behind `Embedder` / `SimilaritySearch` interfaces; `ExactCosine` is unoptimised.

## What was built
- Stable content-derived ids; typed records; parameterised TypeQL (`given` stage), validated labels.
- Versioned migrations per pack with checksums, recorded atomically; automatic export before migrating a
  populated database; restore path tested.
- `Memory`: batch ingestion (all or nothing, skips existing ids), reviews / supersessions / alternatives
  stamped by GUPI's clock, provenance-aware retrieval, and `ask()`.
- Example: `examples/quickstart.py`.

## Tests (all against the live 3.14.1 server; none skipped)
`uv run pytest -q`: **59 passed**.

| File | Tests | Covers |
|---|---|---|
| unit/test_typeql.py | 14 | label validation (injection shapes), parameter typing, datetimes |
| unit/test_temporal.py | 7 | half-open intervals, precision windows, answer combination |
| unit/test_status.py | 3 | review history, ties, supersession |
| unit/test_records.py | 3 | stable ids, proposition keys, input validation |
| unit/test_embedding.py | 4 | codec, exact search, replaceable interface |
| integration/test_claims.py | 8 | the four ADR scenarios, review history vs TypeDB, idempotent decisions, clock guard |
| integration/test_temporal_queries.py | 5 | not-yet-known vs unknown vs false, uncertain bounds, corrections, retraction |
| integration/test_ingest.py | 7 | duplicates, multiple sources, crash mid-transaction, resume after failed batch, conflicts, hostile text |
| integration/test_migrations.py | 4 | apply once, populated migration + backup + restore, checksum and numbering guards, failed migration not recorded |
| integration/test_smoke.py | 4 | server version, round trip, native-vector canary, function redefine |

Not tested: concurrent writers (TypeDB's `@key` on `gupi-id` is the backstop, but no test races two
writers); large volumes; performance.

## Decisions (ADRs)
0001 claims as typed relations, one per attestation · 0002 embeddings without native vectors ·
0003 bitemporal semantics and the five answers · 0004 migrations, safe queries, idempotency.

## Limitations
- Ingestion issues one or two small queries per record: correct, but slow for large batches.
- `ask()` reads all claims for one proposition and evaluates valid time in Python; there is no broad
  search, traversal or ranking yet (Phase 4).
- Supersessions cannot be undone; nothing stops two alternatives both being accepted (Phase 3 policy).
- Referent ids are chosen by the caller; no identity resolution (Phase 3). `mention`, `reference`,
  `context` and `identity` exist in the schema but have no API yet.
- Value comparison in `ask(values=...)` is exact equality.
- The transaction-time guard is per claim, not a global monotonic clock.
- No CLI (deprioritised as instructed).

## Commits
`5f5603a` records, ids, safe TypeQL, review status · `486f1b4` ontology, migrations, ingestion,
retrieval · plus this documentation commit.

## Next
Phase 2 proposal: docs/phase-2-plan.md.
