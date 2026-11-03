# Two-document authoring trial: report (template)

To be filled after the trial, from the logs. Every figure is a count, with its denominator. Nothing is
compared with a threshold.

## 0. What was run
- **Versions used:** the SHA-256 manifest of the guidelines, template, scoring protocol and mappings, and
  the freeze hashes of A's and B's files.
- **People:** who acted as A, B, the reviewer and the two auditors (roles only, if they prefer), and any
  declared connections.
- **Systems:** whether any software system was also run (owner decision). If so, which, and under which
  mapping.

## 1. Conclusion accuracy
For each set of scored answers: B against A's frozen gold, B against the adjudicated gold, and any system.

| Answers | n | A = 1 (value and uncertainty right) | c = 1 (value right) | by frame: recorded / actual / unspecified | by gold status |
|---|---|---|---|---|---|
| B vs A's frozen gold | | | | | |
| B vs adjudicated gold | | | | | |

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
  - evidence standing, including dry-check point D3: asserter or record?
  - alternatives added
  - `implied` versus `inferred`

| Category | Count | Main causes | Guideline change suggested |
|---|---|---|---|

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
| guidelines | A / B | | 60-120 each | |
| world script | A | | 60-90 | |
| document A, document B | A | | 60-90 | |
| gold A, gold B | A | | 60-90 | |
| questions | A | | 30-60 | |
| second annotation | B | | 90-150 | |
| export fixes | A / B | | | |
| adjudication | A and B | | 60-90 each | |
| audit | auditors | | | |

## 8. Representational limitations
From `limitations.csv`: counts by where (guidelines, gold format, GUPI v1, v2 proposal, schema) and by
severity, with the coverage-check results.

## 9. Defects found, and recommendation
- **Defects** in the guidelines, template, contract or mappings revealed by the trial. Each one is concrete,
  with its evidence. Only these justify a change.
- **Recommendation** to the owner: proceed to the mini-pilot, repeat the trial, or revise the estimate or
  scope (README.md, Decision after the trial).
