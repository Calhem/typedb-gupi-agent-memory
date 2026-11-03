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

## Roles
| Role | Who (proposed) | Does | Must not |
|---|---|---|---|
| Primary author (A) | the owner | world script, both documents, gold for both, the questions and their gold answers | read GUPI's code or schema |
| Second annotator (B) | to be confirmed | annotate both documents independently from the documents and guidelines only; answer the six questions from the documents | see the world script or A's gold before both are frozen |
| Implementer | (this codebase's developer) | compute the comparison, run the coverage check after the gold is frozen, write the trial report | author, annotate or adjudicate |

The gold is written by people, not drafted by a language model. If any tool helps with the documents' prose,
it is recorded in the time log's notes.

## Procedure
1. A and B read the guidelines (logged).
2. A writes the world script, then Document A and Document B.
3. A writes the gold for each document, then the six questions and their gold answers.
4. B annotates both documents and answers the questions, independently.
5. **Freeze:** A and B each send the implementer the SHA-256 of their files before seeing each other's work.
6. **Comparison:** the implementer lists every difference, field by field, in `disagreements.csv`.
7. **Adjudication:** A and B meet, and resolve each difference or mark it as a genuine disagreement. Each
   resolution, its cause and any guideline change needed are recorded.
8. **Coverage check:** the implementer checks each adjudicated gold claim and question against:
   - GUPI v1 as it is today
   - the v2 proposal
   - the guidelines' gold format

   Each mapping is written after the freeze, and is lossy where the categories differ (bias-audit-v0.md, B1).

   Anything that cannot be expressed is logged in `limitations.csv`. Authors log the limitations they notice
   while writing in the same file.
9. **Trial report:** the logs, the measures below and a recommendation to the owner.

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

## Measures reported (descriptive only)
- minutes per document, per document's gold and per question, set against authoring-estimate.md
- claims per document, from each annotator
- role-filled-claim precision, recall and F1 between A and B before adjudication
- Cohen's kappa for support and acceptance
- agreement on the six answers, their bases and their interval modes
- disagreements by category and cause; limitations by where and severity

With roughly 15-25 claims, F1 and kappa are far too noisy to compare with the 0.8 and 0.6 thresholds in
m1-protocol.md §8. They are reported as counts with the raw table, not as a pass or a fail.

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
