# Two-document human feasibility trial: report (template)

To be filled after the trial, from the logs. Every figure is a count, with its denominator. Nothing is
compared with a threshold.

**In the human feasibility trial** (no system run):
- Required: §0, §5, §5a, §7, §8 and §9.
- §1-§4 and §6 apply only when contract answers are scored and audited (the mini-pilot onwards). Mark them
  "not applicable".

## 0. What was run
- **Versions used:** the SHA-256 manifest of the guidelines and template, including any revision made in
  step 2.
- **People:** P1 (reviewer), P2 (author) and P3 (annotator), by role only if they prefer, from
  `roles-log.csv`.
  - every overlapping role, and the steps it affected
  - any declared connections
  - whether P2 is the owner
- **Systems:** none were run, in a feasibility trial. Anything else is stated here.
- **Frozen files:** the hashes of P2's and P3's files, confirmed unchanged at adjudication.

## 1. Conclusion accuracy
For each set of scored answers: the annotator's against the author's frozen gold, and against the adjudicated gold.

| Answers | n | A = 1 (value and uncertainty right) | c = 1 (value right) | by frame: recorded / actual / unspecified | by gold status |
|---|---|---|---|---|---|
| annotator vs frozen gold | | | | | |
| annotator vs adjudicated gold | | | | | |

## 2. Evidence-supported accuracy
An answer counts as evidence-supported when A = 1, **and** e = 1 (all essential evidence cited), **and** the
audit's X4 = yes (the cited segments support the answer).

| Answers | n | evidence-supported | A = 1 with e < 1 (`incomplete-evidence`) | multi-source questions: complete-evidence rate |
|---|---|---|---|---|

## 3. Correct but unmatched
Answers the audit judged correct (X7 = yes) for which no accepted form matched (c = 0).

| Question | Answer as given | Gold forms | Missing form? | Proposed amendment (recorded, not applied) |
|---|---|---|---|---|

## 4. Contract failures
| Type | Count | Examples |
|---|---|---|
| not valid JSON, or a field missing | | |
| unknown label or value type | | |
| unknown segment id | | |
| limits exceeded | | |

## 5. Annotator disagreements
- **Source:** `disagreements.csv`, after the freeze and before adjudication.
- **Agreement:**
  - role-filled-claim precision, recall and F1
  - Cohen's kappa for commitment, standing, frame and status
  - all with their raw tables
- **Disagreements** by category and by cause, and the adjudication outcomes, including `unresolvable`.
- **Named checks:**
  - frame classification
  - evidence standing (judged for the originating source) and transmission
  - alternatives added
  - `implied` versus `inferred`

| Category | Count | Main causes | Guideline change suggested |
|---|---|---|---|

## 5a. Usability
From the participants' notes, the time log's export-fixes entries and the exporter's error lists:
- what slowed each participant down, in the guidelines and in the template
- export errors by type, and the time taken to fix them
- fields left empty that should have been filled, and fields that could not be filled at all
- P1's review points, and the decisions taken on them (`review-decisions.md`)

## 6. Auditor agreement
| Item | n | Both agree | Cohen's kappa | Disagreements resolved as |
|---|---|---|---|---|
| X1 explanation consistent | | | | |
| X2 unsupported content | | | | |
| X3 each citation supports | | | | |
| X4 citations together support | | | | |
| X5 consistent with uncertainty | | | | |
| X6 right for the wrong reason | | | | |
| X7 value correct on meaning | | | | |

The hand check of the deterministic scoring gives its own figure: answers where the hand score differs from
the rule-based score, with causes.

## 7. Authoring and annotation time
From `time-log.csv`, set against authoring-estimate.md.

| Task | Person | Minutes | Estimate (minutes) | Notes |
|---|---|---|---|---|
| review | P1 | | 120-180 | |
| guidelines | P2 / P3 | | 60-120 each | |
| world script | P2 | | 60-90 | |
| document A, document B | P2 | | 60-90 | |
| gold A, gold B | P2 | | 60-90 | |
| questions | P2 | | 30-60 | |
| annotation | P3 | | 90-150 | |
| export fixes | P2 / P3 | | | |
| adjudication | P2 and P3 (P1 if facilitating) | | 60-90 each | |

## 8. Representational limitations
From `limitations.csv`: counts by where (guidelines, gold format, GUPI v1, v2 proposal, schema) and by
severity, with the coverage-check results.

## 9. Defects found, and recommendation
- **Defects** in the guidelines, template, contract or mappings revealed by the trial. Each one is concrete,
  with its evidence. Only these justify a change.
- **Recommendation** to the owner: proceed to the mini-pilot, repeat the trial, or revise the estimate or
  scope (README.md, Decision after the trial).
