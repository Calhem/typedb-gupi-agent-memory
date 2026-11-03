# Memory Formation Engine: plan for milestones 6B-6D

Date: 2026-11-03. Status: **proposal, for approval before 6B starts.**

**Each milestone:**
- is on the formation branch
- ends with a stop for review
- keeps the existing ingestion path, v1 (the default), v2, the frozen benchmarks and the budget ledger
  unchanged
- makes no paid calls without explicit approval

## 6B: Candidates from the offline extractor, stored apart from memory
- **Schema:** apply the additive `core/0011` (integrity-and-schema.md §3), after approval, with a
  populated-database migration test.
- **Extractor:** a rule extractor `rules:v2` that emits `gupi.candidate/1` sets. It should fix what the
  audit found, within its simple patterns:
  - "since", including leading "Since March, ...", becomes `holds-since` (A1)
  - a "Correction:" cue becomes a stated `corrects` relation (A2)
  - "no longer" and "does not" become negative polarity (A3)
  - "X told me" and "reportedly" become a reported attribution (A4)
  - "will" and "plans to" become `planned` (A5)
  - the time reading becomes part of the candidate (A7)

  `rules:v1` stays, unchanged, as the default.
- **Storage:** an opt-in `formation.extract(memory, extractor, observations)` validates each set and stores
  valid candidates as `memory-candidate`, with their run. It **creates no claims.** Invalid items are
  reported with reasons, and nothing is repaired.
- **Tests:**
  - per-pattern unit tests, including start against holds-since on the Phase 2 development sentences
  - storage round trip and idempotent re-runs, on the live server
- **Exit:** development sentences produce valid candidate sets; the since/start, negation and correction cases
  are correct; existing tests unchanged.

## 6C: Formation: from candidates to claims, review-gated
**Separate, recorded decisions** for each candidate:
- **salience:** keep or ignore
- **support:** how strongly the passage supports the candidate
- **acceptance:** hypothesis, or a recorded acceptance policy (default: always a hypothesis, as today)

**Mapping to claims:**
- valid time by `formation.validate.valid_time`, with `valid-from-basis` recorded
- polarity, modality, commitment and attribution recorded
- participants resolved to scoped referents, as the current contract does
- `formed-into` links each claim to its candidate

**Corrections:** a stated `corrects` relation becomes a *suggested* supersession in the review queue. Only a
reviewer creates it.

**Non-actual modality:** planned, hypothetical and other non-actual candidates are not formed into ordinary
claims, so a plan is never answered as a fact. They stay as candidates until a modality-aware claim type is
approved.

**Exit:** end-to-end tests from observation to candidates to claims to v2 answers, covering:
- since against start
- a negation's scope
- a correction suggestion
- a reported statement
- idempotence

Answers on data ingested by the old path are unchanged.

## 6D: Evaluation, and an optional LLM extractor
**Evaluation:** on the development split only, under the frozen protocol:
- per-field accuracy of candidates: time kind (since against start), polarity, modality, attribution,
  correction relations
- the share of candidates that validate
- what formation adds over `rules:v1`

**LLM extractor (optional):** a Claude extractor emitting `gupi.candidate/1`.
- It runs behind the fail-closed ledger, and **only with the owner's approval of a budget**.
- Its prompts are pinned by hash.

**Not before the protocol allows:** held-out runs, and the M1 pilot. Neither starts in 6D without separate
approval.

**Decision point for the owner:** whether formation replaces the direct extraction path by default. Until
then, both remain.

## Dependencies and open points
- **The formation design document** (`docs/specialist/memory-formation-engine.md`) is on the
  `feature/specialist-evaluation` branch, not on main. 6C's salience, support and acceptance decisions should
  follow it, or a revision of it, once approved.
- **How "held at some time in a window" claims are stored** (`holds-at` over a month) is unresolved
  (candidate-ir.md §5). Until a representation is approved, such candidates are kept, not formed.
