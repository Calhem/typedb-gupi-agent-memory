# Memory Formation Engine (Phase 6)

Status: **Phase 6A (foundations) and 6B (offline candidate extraction) done on
`feature/phase-6-memory-formation`; 6C is at a design checkpoint; not merged.**
- Nothing here changes how GUPI ingests, extracts or answers today.
- The new package `gupi.formation` is used by no other code, and stores nothing.

| Document | Contents |
|---|---|
| [audit.md](audit.md) | The existing pipeline, and seven gaps (A1: "since" becomes an exact start, reproduced) |
| [candidate-ir.md](candidate-ir.md) | The versioned candidate representation `gupi.candidate/1`, its validation, and the provisional valid-time mapping |
| [integrity-and-schema.md](integrity-and-schema.md) | What TypeDB enforces against what the application checks; the proposed additive schema `core/0011` (not applied) |
| [plan-6b-6d.md](plan-6b-6d.md) | Milestones 6B-6D, for approval |
| [rules-v2.md](rules-v2.md) | 6B: the offline candidate extractor `rules:v2`, its scope, cues and known limits |
| [6c-design-checkpoint.md](6c-design-checkpoint.md) | 6C: the minimum fields to form candidates into claims; a revised schema (0011 claim provenance, 0012 candidate store) for decision |

6B results: ../evaluation/phase-6b-extraction.md.
