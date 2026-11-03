# Memory Formation Engine (Phase 6)

Status: **6A (foundations), 6B (offline candidate extraction) and 6C (the minimal formation pathway, with
core/0011) done on `feature/phase-6-memory-formation`; not merged.** core/0012 (candidate storage) is not
implemented.
- **Unchanged:** the existing ingestion, `rules:v1` and answer semantics v1 and v2.
- **Opt-in:** formation is a separate pathway (`gupi.formation.form`), used only when called.

| Document | Contents |
|---|---|
| [audit.md](audit.md) | The existing pipeline, and seven gaps (A1: "since" becomes an exact start, reproduced) |
| [candidate-ir.md](candidate-ir.md) | The versioned candidate representation `gupi.candidate/1`, its validation, and the provisional valid-time mapping |
| [integrity-and-schema.md](integrity-and-schema.md) | What TypeDB enforces against what the application checks; the proposed additive schema `core/0011` (not applied) |
| [plan-6b-6d.md](plan-6b-6d.md) | Milestones 6B-6D, for approval |
| [rules-v2.md](rules-v2.md) | 6B: the offline candidate extractor `rules:v2`, its scope, cues and known limits |
| [6c-design-checkpoint.md](6c-design-checkpoint.md) | 6C: the minimum fields to form candidates into claims; a revised schema (0011 claim provenance, 0012 candidate store) for decision |

6B results: ../evaluation/phase-6b-extraction.md.
| [formation.md](formation.md) | 6C: the formation pathway and its policy (`formation:v1`) |
| [6c-dev-demo.md](6c-dev-demo.md) | 6C: the development-only end-to-end demonstration (not a benchmark) |
