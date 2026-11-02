# Phase 1 proposal: core ontology and persistence

Goal (gate): ingest and retrieve structured evidence with a source trace; reruns do not duplicate it.

Small steps, each tested and committed on `feature/phase-1-core`:

1. **Deterministic ids.** `gupi-id` derived from content: observations from `(source id, source record
   id or offset, content hash)`; facts from `(type, role players, time bounds, evidence)`. Same input,
   same id, so a rerun finds the existing record instead of adding one.
2. **Schema setup and versioning.** A `schema-version` record in the database; `noodle_memory.schema`
   applies numbered migration files in order (types via `define`, functions via `redefine`), with a
   documented recovery path (export, rebuild, replay) rather than pretending every change is reversible.
3. **Typed Python records.** Small dataclasses (`Source`, `Observation`, `FactDraft`, `Review`,
   `ValidTime`) and one module that turns them into parameter-safe TypeQL (escaped strings, checked
   type and role names from the schema, never raw user text in query structure).
4. **Idempotent ingestion.** `Memory.ingest_records(...)`: insert-if-absent in one write transaction per
   batch; returns what was new and what already existed.
5. **Retrieval with trace.** `Memory.facts_about(referent, believed_at=..., valid_at=...)` returning
   facts with their evidence spans, sources, reviews and three-valued valid-time status.
6. **Core carrier relations** for attribute-valued claims (e.g. a named property with a string/number/
   date value), so domain authors rarely write their own.
7. **Minimal CLI**: `gupi init`, `gupi ingest-file <jsonl>`, `gupi facts <id> [--as-of] [--valid-at]`.

Out of scope for Phase 1: LLM extraction (Phase 2), identity resolution logic and conflict policy
(Phase 3), embeddings in retrieval (Phase 4), any connector beyond a JSONL/text fixture.

Questions for the owner:
- Package name: the brief uses `noodle_memory`; the product is GUPI. Keep `noodle_memory`, or rename to
  `gupi` now while it is cheap?
- GitHub: create a public `Calhem/typedb-noodlelab-GUPI` repository and push, or keep it local for now?
- Licence: Apache-2.0 (TypeDB's driver licence) unless you prefer MIT.
