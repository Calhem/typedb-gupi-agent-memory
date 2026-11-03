# Two-document authoring trial (before the eight-document mini-pilot)

Date: 2026-11-03. Status: **approved by the owner; not started. Nothing has been authored.**

## Purpose
Before the eight-document mini-pilot, measure three things on the smallest useful sample:
1. **Authoring time:** real minutes per task, logged at the time, not estimated afterwards.
2. **Annotation disagreements:** where two people annotating the same documents differ, and why.
3. **Representational limitations:** what the guidelines, the gold format, GUPI's current schema (v1) or the
   proposed v2 semantics cannot express.

The trial does not test GUPI, and no system is run on its data. It sets no M1 thresholds: they stay
provisional until reviewed (m1-protocol.md §2).

## Prerequisite: annotation guidelines, draft v0
The guidelines are in guidelines-v0.md (revision 2), with:
- a bias audit, in bias-audit-v0.md
- the primary scoring protocol (a common structured answer contract), in scoring-protocol-v0.md
- an experimental secondary metric for free-text answers, in scoring-nl-experimental-v0.md
- a spreadsheet annotation template, in annotation-template/ (JSON Lines remains the canonical format)
- an independent-review checklist, in review-checklist-v0.md

The guidelines and checklist are approved for external review. Everything stays provisional, and the
scoring protocol is not frozen.
- They are **implementation-neutral** (owner condition, 2026-11-03). Their categories are not derived from
  GUPI's schema, TypeQL, ADR 0009 or any system's truth classification.
  - Answers carry their own statuses: `stated`, `inferred`, `disputed`, `insufficient` and
    `not-yet-available`.
  - Each answer also carries its evidence sets.
- Mapping the gold onto GUPI v1, the v2 proposal or any other representation happens only in the coverage
  check, after the freeze. It never changes the gold.
- For the trial they are **draft v0**. The trial is expected to change them; they are frozen only before the
  mini-pilot.

## Scope
**World script:**
- one organisation and one subcontractor
- 6-8 fictional people
- about three months of world time
- 10-15 dated events

**Two documents:**
- **Document A:** meeting minutes, about 400 words.
- **Document B:** an email thread written about three weeks later in world time, about 400 words, with a
  quoted earlier message and a forward.

**Phenomena:** across the two documents, each of these appears at least once:

| Phenomenon | Exercises |
|---|---|
| A role change with a stated start | starts, spells |
| A termination, then a reinstatement | Q3, R3-R6 |
| A moved deadline stated as a month without a year | the date fix |
| A late correction: B corrects something stated in A | corrections, as-of history |
| An explicit negation ("no longer responsible for ...") | negation, independent of an end date |
| A conflicting report from a different source | CONTESTED |
| A multi-party approval (who approved, on whose behalf, under what condition) | n-ary claims |
| An unconfirmed rumour | modality, support |
| Irrelevant chatter, a pronoun and a role reference | salience, reference |

**Six questions:**
- at least one straightforward retrieval question
- one asked as of an earlier belief time
- one with gold UNKNOWN or CONTESTED
- each with its interval mode

## Roles and responsibilities
### Needs an independent human
These cannot be done by the implementer, who designed GUPI and drafted the guidelines.

| Task | Who | Why |
|---|---|---|
| Review the reviewer package: the guidelines, the template, the scoring contract and the system mappings | **independent reviewer**, unfamiliar with GUPI | author familiarity (bias-audit-v0.md, B1, B17) |
| Write the world script, both documents, the six questions and their gold answers, with accepted forms | **primary author (A)**: proposed, the owner | gold must not come from the implementer |
| Annotate both documents independently, and answer the questions in the sheets | **second annotator (B)**: to be confirmed | independence |
| Adjudicate the differences | **A and B together** | judgement about the gold |
| Audit the explanations and evidence (scoring-protocol §6, X1-X7) | **two auditors** who built no evaluated system: to be confirmed | judgement of support and correctness |
| Check the deterministic scoring by hand (a sample, or all six questions in the trial) | the same two auditors, or two others who did not build the scorer | the scorer's error rate |
| Decide: changes after the review; whether any software system is also run on the trial questions; proceed, repeat or revise after the trial; any freeze | **owner** | approval gates |

### Can be done internally (implementer)
- Assemble the reviewer package and its SHA-256 manifest.
- Maintain the template and the exporter. Export and validate each annotator's sheets, and return errors to
  the annotator to fix (their time is logged).
- Receive the freeze hashes. List the differences between A and B mechanically (`disagreements.csv`), and
  compute the agreement figures.
- Draft and maintain the system mappings, which the reviewer checks.
- Apply the deterministic scoring rules to the contract answers. For six questions this can be done with a
  small script or by hand; either way it is checked by the hand audit.
- Prepare blinded, shuffled audit sheets.
- Run the coverage check against GUPI v1 and the v2 proposal.
- Compile the trial report from the logs, using trial-report-template.md.

The implementer never authors, annotates, adjudicates, audits, judges neutrality, or freezes anything.

The gold is written by people, not drafted by a language model. If any tool helps with the documents' prose,
it is recorded in the time log's notes.

## Procedure
0. **Independent review** of the reviewer package (reviewer-package/README.md). The owner decides which of
   the reviewer's points to act on before the trial starts.
1. A and B read the guidelines (logged).
2. A writes the world script, then Document A and Document B.
3. A writes the gold for each document, then the six questions and their gold answers, with accepted forms
   (scoring-protocol §4.1.1).
4. B annotates both documents and answers the questions in the sheets, independently. B's answers become
   contract answers by the fixed mapping (system-mappings-v0.md, H-annotator).
5. **Export:** each annotator's sheets are exported and validated (`scripts/annotation_export.py`). Errors go
   back to their author to fix.
6. **Freeze:** A and B each send the implementer the SHA-256 of their files, before seeing each other's
   work.
7. **Comparison:** the implementer lists every difference, field by field, in `disagreements.csv`.
8. **Adjudication:** A and B meet, and resolve each difference or mark it as a genuine disagreement. Each
   resolution, its cause and any guideline change needed are recorded.
9. **Scoring:** B's contract answers are scored deterministically, against A's frozen gold and against the
   adjudicated gold.
10. **Audit:** the two auditors complete X1-X7 for each answer independently, then compare. They also check
    the scoring by hand.
11. **Coverage check:** the implementer checks each adjudicated gold claim and question against:
    - GUPI v1 as it is today
    - the v2 proposal
    - the guidelines' gold format

    Each mapping is written after the freeze, and is lossy where the categories differ (bias-audit-v0.md,
    B1). Anything that cannot be expressed is logged in `limitations.csv`. Authors log the limitations they
    notice while writing in the same file.
12. **Trial report:** trial-report-template.md, filled from the logs, with a recommendation to the owner.

## What is recorded
Templates in this folder (CSV, one row per entry):
- **`time-log.csv`:** person, task, start, end, minutes, interruptions, notes. The tasks are:
  - guidelines
  - world-script
  - document-A, document-B
  - gold-A, gold-B
  - questions
  - second-annotation
  - adjudication
- **`disagreements.csv`:** document, item (claim or question id), field, A's value, B's value, category,
  cause, resolution, guideline change needed.
  - **Categories:**
    - missed claim, extra claim
    - role assignment, value, modality, assertor
    - time phrase, explicit vs inferred date
    - support, salience, acceptance
    - answer kind, basis, interval mode
  - **Causes:**
    - guideline unclear
    - guideline silent
    - document ambiguous
    - annotator slip
    - genuine disagreement
- **`limitations.csv`:** found by (author, annotator, coverage check), document, item, what could not be
  represented, where (guidelines, gold format, GUPI v1, v2 proposal, schema), example, severity, proposal.
  - **Severities:**
    - blocks a question
    - loses detail
    - cosmetic

## Measures reported
See trial-report-template.md:
- conclusion accuracy
- evidence-supported accuracy
- correct-but-unmatched answers
- contract failures
- annotator disagreements
- auditor agreement
- authoring and annotation time

All are descriptive. With six questions and roughly 15-25 claims, nothing is compared with a threshold.

## Decision after the trial (owner)
- **Proceed** to the eight-document mini-pilot, with the guidelines revised from the logs, which is
  expected.
- **Repeat the trial** with revised guidelines, if the disagreements show the answer kinds, the bases or
  the gold format cannot be applied consistently.
- **Revise the estimate or scope,** if the measured minutes are far from the estimate (for example more than
  twice), or if limitations block whole question families.

Limitations attributed to GUPI v1 or the v2 proposal become inputs to the formation milestone and to ADR
0009. They do not change the trial's gold.

## Data handling
- Fictional organisations and people only, with no real names, nothing confidential and no personal data.
  The repository is public.
- Trial data is not held-out data, and is never reused in the development or held-out splits.
- A and B keep their files locally until the freeze. The logs, documents and adjudicated gold are committed
  with the trial report, under `evaluation/m1/trial/`.
