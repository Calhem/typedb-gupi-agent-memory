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
| Fix | Commit | Document | Tests |
|---|---|---|---|
| R1 statement structure | `9ea644b` | [r1-structural-fidelity.md](r1-structural-fidelity.md) | `tests/unit/test_stage4_r1_structure.py` (13), store path in `tests/integration/test_stage4_integrity.py` |
| R2 bare retractions | `082f4e0` | [r2-bare-retractions.md](r2-bare-retractions.md) | `tests/unit/test_stage4_r2_retractions.py` (7), store path |
| R3 allegation context | `b60e6c5` | [r3-allegation-propagation.md](r3-allegation-propagation.md) | `tests/unit/test_stage4_r3_allegations.py` (6), store path |

**Review fixes** (final review, [merge-readiness.md](merge-readiness.md)): `e2b251e` whole-word predicates (R1),
`34e5243` retractions read from broken responses (R2), `848696a` persistence and retrieval tests, and a code-hash
list that includes `fidelity.py`.

## Check against the frozen Stage 3B responses (private, read-only)
The 32 recorded Stage 3B responses were replayed through the fixed interface and formation in a disposable
database (private record, `gupi-stage3-private` commit `61c6d91`). This is a check, not a new result: the frozen
Stage 3B figures stand, nothing was tuned, and no passage or response is published.

| | Stage 3B (frozen) | After R1–R3 |
|---|---|---|
| candidates | 30 | 31 (+1: the bare retraction) |
| formed / review / withheld / rejected | 17 / 4 / 9 / 0 | 14 / 8 / 9 / 0 |
| severe errors formed as facts | 3 (X3-09, X3-27, X3-28) | **0**: all three go to review |
| other decisions | – | unchanged (the 14 remaining formed claims are the same) |
| store rejections, failures, supersessions | 0, 0, 0 | 0, 0, 0 |

- **X3-27, X3-28:** review, "statement structure not verified" (R1).
- **X3-09 employment:** review, commitment unknown (R3).
- **X3-17:** the bare retraction is now a review item with an unestablished target (R2); the retracted claim stays
  believed until a reviewer acts.
- **X3-19:** still review, now for two reasons: its hedge and its structure (R1).

## What still holds
- **Provenance, time and corrections:** evidence spans, time readings, `via`, forwarded-copy handling and D3
  correction suggestions are unchanged; every existing test of them passes.
- **Nothing is applied automatically:** no supersession, identity merge or target choice is added.

## Remaining integrity risks
- **Structural, not semantic:** a misleading predicate whose object directly follows it is not detected (R1).
- **Lexical cues:** retractions and allegations worded outside the listed phrases are missed unless the model marks
  them (R2, R3).
- **Review volume rises:** "shortest verb" statements with an object participant, and every assertion near an
  allegation cue, now wait for review.
- **Not yet in answers:** a pending retraction is visible in the review queue, not flagged on the claims it may
  retract.
- **Deferred:** "former" (R4), within-passage surname coreference (R5), same-named people (S8), paraphrased copies
  (L4), and `rules:v2` reading retractions.
- **One synthetic test author:** the fixtures were written by the developer; an externally written corpus (R10)
  is still the main gap before adoption.
