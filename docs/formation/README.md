# Memory Formation Engine (Phase 6)

Status: **6A (foundations), 6B (offline candidate extraction) and 6C (the formation pathway, hardening,
and the candidate store, core/0011 and core/0012) done on `feature/phase-6-memory-formation`; not merged.**
- **Unchanged:** the existing ingestion, `rules:v1` and answer semantics v1 (the default) and v2.
- **Opt-in:** formation (`gupi.formation.form`) and the candidate store (`gupi.formation.store`) are separate
  pathways, used only when called.

| Document | Contents |
|---|---|
| [audit.md](audit.md) | The existing pipeline, and seven gaps (A1: "since" becomes an exact start, reproduced) |
| [candidate-ir.md](candidate-ir.md) | The versioned candidate representation `gupi.candidate/1`, its validation, and the valid-time mapping |
| [integrity-and-schema.md](integrity-and-schema.md) | What TypeDB enforces against what the application checks; the original schema proposal |
| [plan-6b-6d.md](plan-6b-6d.md) | Milestones 6B-6D |
| [rules-v2.md](rules-v2.md) | 6B: the offline candidate extractor `rules:v2`, its scope, cues and known limits |
| [rules-v2.1.md](rules-v2.1.md) | `rules:v2.1`: the D1 (pronouns) and D2 (unsupported expressions) corrections; how to select a version |
| [6c-design-checkpoint.md](6c-design-checkpoint.md) | 6C: the minimum fields to form candidates into claims; the split into 0011 and 0012 |
| [formation.md](formation.md) | 6C: the formation pathway and its policy (`formation:v1`) |
| [6c-dev-demo.md](6c-dev-demo.md) | 6C: the development-only end-to-end demonstration (not a benchmark) |
| [6c-hardening-audit.md](6c-hardening-audit.md) | 6C hardening: where evidence could be silently strengthened (H1-H11) |
| [6c-hardening.md](6c-hardening.md) | 6C hardening: three separate dimensions (temporal, evidential, acceptance) and the qualification on v2 answers |
| [candidate-persistence.md](candidate-persistence.md) | Candidate persistence assessment (option C approved) |
| [candidate-store.md](candidate-store.md) | The candidate store (core/0012): schema, lifecycle, review semantics, belief time, risks |

**Results:**
- 6B: ../evaluation/phase-6b-extraction.md
- 6C adversarial, development-only: ../evaluation/phase-6c-adversarial.md
