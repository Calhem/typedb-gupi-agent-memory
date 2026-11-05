# Stage 3C results: model-assisted adjudication (exploratory)

**Status (2026-11-05):** adjudication done by a model, not by a person. **These results are exploratory and are
not independently human-verified.** Stage 3C is not merged.

## How the results were produced
1. **The corpus:** 32 fictional passages, written by Claude.
2. **The original gold annotations (gold v1):** also written by Claude.
3. **The adjudication:** ChatGPT (a different model family) reviewed 19 selected cases from the private review
   package described in [adjudication-protocol.md](adjudication-protocol.md): the 12 disputed Stage 3B items and
   7 supplementary cases. The owner ran it; Claude did not adjudicate.
4. **Frozen first:** the decisions were recorded unchanged and hashed **before** gold v2 was generated.
5. **Gold v2 is an overlay** on gold v1, derived mechanically from the decisions:
   - an appropriate abstention plus a gold error → the assertion is removed from the expected set
   - an exact or alternative decision → the candidate is accepted
   - a gold error on an accepted candidate → a field correction
   - a gold error with no specified change → flagged, and the v1 assertion kept
6. **Rescoring:** the overlay was applied to the frozen Stage 3B scorer output. The scorer itself is unchanged,
   because R7 is not approved.
7. **What did not change:** gold v1, the Stage 3B results, the extractor, the prompt and the responses. No
   extractor change was made and no model was run again.

**Provenance:** private commit `a17a0c2` in the local `gupi-stage3-private` repository. It holds the frozen
decisions, the gold v2 overlay, the rescoring script and its output. None of it is published.

## Results
| Metric | Gold v1 | Gold v2 |
|---|---|---|
| Model precision | 21/30 (0.70) | 24/30 (0.80) |
| Model recall | 21/39 (0.54) | 24/33 (0.73) |
| Model F1 | 0.61 | 0.76 |
| Rules baseline recall | 3/39 | 3/33 |
| Severe errors | 5 | 4 |
| Severe errors admitted as facts | 3 | 3 |
| Claimant kind accuracy | 3/6 | 5/6 |

**Notes on the figures:**
- **The rules baseline's precision** is 3/3 under both versions. None of its candidates was in the review set.
- **Two readings of the protocol:** the gold v2 column applies the reviewer's classification both ways, so two
  candidates that the frozen scorer matched become partial. If only upgrades were applied (the protocol's
  narrower wording), the model would score 26/30 precision, 26/33 recall and an F1 of 0.83. The table uses the
  stricter figure.
- **Formation counts:** the rescoring does not recompute formation, so no revised formation counts are given.
  The Stage 3B counts (17 formed, 4 review, 9 withheld, 0 rejected) are unchanged, because formation was not run
  again.

**What the F1 change means:** the rise from 0.61 to 0.76 reflects **revised evaluation annotations**, not better
model performance. The responses are the same.
- **Six fewer expected assertions:** the reviewer judged that the model was right to write nothing in five cases
  (six gold assertions). They include two same-named people the format cannot keep apart, an employment stated
  only as a false test instruction, a bare retraction and a surname-only denial.
- **Five candidates accepted as correct alternatives:** the same proposition written in a different but valid
  shape (for example, the object kept as free text instead of a participant). One of them is the extracted
  question, which also clears one severe-error label.
- **Two claimant-kind gold errors:** the passage gives only a name, so `unknown` follows the frozen rule.

## The central finding is unchanged: three severe errors were admitted as facts
These are confirmed by the adjudication: in each case the reviewer did not accept the candidate, and judged that
it should have gone to review rather than being formed.

| Case | Confirmed error |
|---|---|
| X3-09 | an employment formed as an unqualified fact: its "former" status and its allegation context were lost |
| X3-27 | a structurally incorrect predicate/object representation: the relation between the subject, the action and the object participant is not what the source states |
| X3-28 | the same structural error repeated from another source |

**Also confirmed (not formed):**
- **X3-19:** a shared operator represented as a direct operator relationship. The reviewer classed it incorrect.
  Only the source's hedge sent it to review instead of formation.

**Handling that needs improvement (not counted as extraction errors):**
- **Bare retractions and surname-only denials:** the reviewer accepted the abstention, because format 1.1 cannot
  express them, but judged that both should reach a person for review. Today they are dropped, so a retracted
  claim stays formed with no flag.

**Unresolved annotation question:**
- **Item 9 (X3-09):** the reviewer marked a gold error but did not say what the change should be. The v1
  assertion is kept. Writing the correction is left to a person, because the gold's author must not adjudicate
  its own answer.

## Next engineering priorities (proposed, not implemented)
These come from [proposed-remediation.md](proposed-remediation.md). They should become the next implementation
stage, each with regression tests built from synthetic fixtures for the observed failure classes (not from the
private corpus).

| | Change | Failure class it targets |
|---|---|---|
| R1 | preserve predicate/object semantics, with structural fidelity checks (the predicate must carry the words linking subject and object participant; an object participant inside `object_text` is refused) | X3-19, X3-27, X3-28 |
| R2 | represent a bare retraction, and route unresolved corrections and their candidate targets to review | X3-17-type retractions |
| R3 | propagate allegation context to assertions embedded in an allegation, so they cannot be admitted as unqualified facts | X3-09 |

**Distinctions kept in this document:**
- **Confirmed errors:** X3-09, X3-27, X3-28 (formed); X3-19 (review).
- **Unresolved annotation question:** item 9.
- **Proposed remedies:** R1–R3. They are designs only, and need approval.

## Limits
- **One corpus, one author, one model family wrote the passages and gold.** A second model family adjudicated
  19 of the cases; the rest of the gold is unreviewed.
- **Not human-verified.** A human review could still change these figures.
- **An externally written corpus (R10)** remains the main gap before any adoption decision.
