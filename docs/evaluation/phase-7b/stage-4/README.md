# Phase 7B Stage 4: evidence integrity fixes (R1–R3)

Date: 2026-11-05.
- **Branch:** `feature/phase-7b-stage-4-evidence-integrity`, from Stage 3C (`0f4645b`). **Not merged.**
- **Nothing external:** no API call, model inference or model download. $0.
- **Unchanged:** the frozen Stage 3 corpus, gold, prompts, responses and results; the TypeDB schema.
- **Tests:** synthetic fixtures only. No private evaluation passage or answer is copied into a test.

**The aim:** stop the three Stage 3B failure classes that let valid-looking evidence become an unqualified fact,
preferring review over formation whenever a structure cannot be verified. Recall may fall; no new assertion
is ever invented.

## Compatibility: no candidate-format or response-format change
| Fix | Where | Format change | Effect on existing data |
|---|---|---|---|
| R1 statement structure | formation policy (`form.decide`, used by `form()` and the candidate store) | none | a statement whose object participant is not the predicate's direct object, or lies inside its object text, now goes to **review** instead of being formed. Already-formed claims are untouched |
| R2 bare retractions | the offline model interface (`model:candidate-v1.1`) | none: uses the existing 1.1 null-target `retracts` relation on a generic statement | a message that retracts without restating now yields a reviewable candidate; previously nothing |
| R3 allegation context | the offline model interface | none | an assertion inside an allegation (a lexical cue, or an assertion the model marked `allegation`) is no longer `certain`, and takes the alleger's attribution when it has none of its own, so it goes to review |

Candidate ids depend on content: a candidate whose commitment or attribution R3 changes gets a new id, as any
changed content would. Recorded Stage 3B responses still parse; re-running them through the fixed interface
gives different decisions by design, and the frozen Stage 3B results are not regenerated.

## The fixes
Each section is filled in as the fix lands: [r1-structural-fidelity.md](r1-structural-fidelity.md),
[r2-bare-retractions.md](r2-bare-retractions.md), [r3-allegation-propagation.md](r3-allegation-propagation.md).
