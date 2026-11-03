# Two-document human feasibility trial (before the eight-document mini-pilot)

Date: 2026-11-03. Status: **ready for execution; not started. Nothing has been authored.** The next step
needs independent human participants.

## Purpose
Before the eight-document mini-pilot, find out whether people can apply the guidelines, on the smallest
useful sample. Report:
1. **Time:** real minutes per task, logged at the time, not estimated afterwards.
2. **Usability:** what slowed people down in the guidelines and the spreadsheet template.
3. **Consistency:** where the author's gold and an independent annotator's answers differ, and why.
4. **Representational limitations:** what the guidelines or the gold format cannot express. The internal
   coverage check against GUPI is a paper comparison only.

**This is a human feasibility trial.**
- No software system is run: not GUPI, and not any baseline.
- The answer contract, contract scoring and the explanation audit are not used here. They are exercised
  later, in the mini-pilot.
- It sets no M1 thresholds: they stay provisional until reviewed (m1-protocol.md §2).

## Prerequisite: annotation guidelines, draft v0
The guidelines are in guidelines-v0.md (revision 3), with:
- a bias audit, in bias-audit-v0.md
- the primary scoring protocol (a common structured answer contract), in scoring-protocol-v0.md
- an experimental secondary metric for free-text answers, in scoring-nl-experimental-v0.md
- a spreadsheet annotation template, in annotation-template/ (JSON Lines remains the canonical format)
- an independent-review checklist, in review-checklist-v0.md

The scoring protocol, the experimental metric and the system mappings are **not used** in this feasibility
trial, because no system is run.

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

| Phenomenon | What it tests (in the guidelines' terms) |
|---|---|
| A role change with a stated start | states and their start (§7.3) |
| A termination, then a reinstatement | termination and reinstatement (§10) |
| A moved deadline stated as a month without a year | updates; time anchors (§7.1, §11) |
| A late correction: Document B corrects something stated in Document A | corrections; `as_of` questions (§11, §12) |
| An explicit negation ("no longer responsible for ...") | negation, kept apart from an end date (§10) |
| A conflicting report from a different source | `disputed` answers (§12) |
| A multi-party approval (who approved, on whose behalf, under what condition) | participants and roles (§4, §5) |
| An unconfirmed rumour | certainty and standing (§6, §8.1) |
| A forwarded or transcribed statement | transmission (§8.2) |
| Irrelevant chatter, a pronoun and a role reference | references (§3) |

**Six questions:**
- at least one plain retrieval question
- at least one answered by a reason or caveat in a source's own words (`short-text`)
- one asked `as_of` an earlier date
- at least one `recorded` and one `actual` question
- one whose gold is `insufficient` or `disputed`
- each with its frame, and, for periods, its mode

## Participants and roles
Three independent participants, where practical:

| Participant | Role | Does | Must not |
|---|---|---|---|
| **P1** | guidelines reviewer | reviews the reviewer package (step 1). May also help with adjudication, as a facilitator, or check the comparison. | have seen the trial's documents or gold before step 5 |
| **P2** | primary author | writes the world script, two documents, six questions and the gold (step 3) | read GUPI's code or schema; see P3's answers before freezing |
| **P3** | independent annotator | annotates the two documents and answers the six questions from the documents alone (step 4) | see the world script, the gold or P2's notes before freezing |

**Overlapping roles** (for example P1 helping to adjudicate) are allowed, and recorded in `roles-log.csv`
with the steps involved. The report states every overlap.

**Fewer than three people.** If three independent people are not available, the owner decides who doubles
up. The report says so, and treats agreement figures with corresponding caution.

**Owner (not a participant):** decides which review points to act on (step 2), and what happens after the
trial. P2 may be the owner, as proposed earlier; if so, that is recorded too.

**Implementer (internal; not a participant).** Does only clerical and mechanical work:
- assembles and sends the packages, with SHA-256 manifests
- carries files between participants. P3 receives the documents and questions only, never the gold or the
  world script.
- exports and validates the sheets (`scripts/annotation_export.py`), returning errors to their author
- receives the freeze hashes, and keeps the frozen copies unchanged
- lists the differences mechanically, and computes the agreement figures
- runs the paper coverage check
- compiles the report (trial-report-template.md)

The implementer never authors, annotates, adjudicates, judges neutrality, or creates any trial document or
question.

The gold is written by people, not drafted by a language model. If any tool helps with the documents' prose,
it is recorded in the time log's notes.

## Procedure
1. **Independent guidelines review** (P1).
   - P1 receives the reviewer package (reviewer-package/README.md) and returns the short form, their practice
     answers and their time.
2. **Resolve material ambiguities** (owner).
   - Only points that would make annotators disagree, or block annotation, are acted on.
   - Each decision is recorded in `review-decisions.md`, with the change made.
   - The guidelines' revision number and the manifest are updated. Everything else waits for the trial's
     evidence.
3. **Author and freeze** (P2).
   - P2 receives the guidelines as revised in step 2, the template, `time-log.csv` and `limitations.csv`.
   - P2 writes the world script, Document A and Document B, the six questions (with frames), and the gold
     for both documents and all questions, with accepted forms. Scope and guidance: §Scope above, and
     guidelines §17.
   - **Freeze:** P2's files are exported and validated, then P2 sends their SHA-256 hashes. The implementer
     keeps an unchanged copy of the frozen files.
4. **Independent annotation** (P3).
   - P3 receives the guidelines, the template, the two documents and the six questions. They do not receive
     the world script, the gold or any of P2's notes.
   - P3 annotates both documents and answers the questions.
   - **Freeze:** P3's files are exported, validated and hashed in the same way, and an unchanged copy is
     kept.
5. **Compare, adjudicate and document** (P2 and P3, optionally facilitated by P1).
   - The implementer lists every difference between the frozen files in `disagreements.csv`.
   - P2 and P3 resolve each difference, keep both readings (`both-acceptable`), or mark it `unresolvable`,
     recording its cause and any guideline change needed (guidelines §14).
   - The adjudicated gold is a new file. **The frozen files are never edited,** so agreement is measured on
     what each person wrote independently.
6. **Report** (implementer compiles; participants review their own sections).
   - Time, usability, consistency and representational limitations, using trial-report-template.md, with a
     recommendation to the owner.

**Elapsed time:** about one to two weeks, set mainly by the participants' availability.

**Person-time** (authoring-estimate.md):
- P1: about 2-3 hours
- P2: about 4.5-7.5 hours
- P3: about 1.5-2.5 hours
- adjudication: about 1-1.5 hours each

## What is recorded
Templates in this folder (CSV, one row per entry):
- **`time-log.csv`:** person, task, start, end, minutes, interruptions, notes. The tasks are:
  - review
  - guidelines
  - world-script
  - document-A, document-B
  - gold-A, gold-B
  - questions
  - annotation
  - export-fixes
  - adjudication
- **`disagreements.csv`:** document, item (claim or question id), field, the author's value (P2, column
  `value_a`), the annotator's value (P3, column `value_b`), category, cause, resolution, guideline change
  needed.
  - **Categories:**
    - missed claim, extra claim
    - role assignment, value, modality, assertor
    - time phrase, explicit vs inferred date
    - commitment, standing, transmission
    - frame, status, evidence, alternatives, interval mode
  - **Causes:**
    - guideline unclear
    - guideline silent
    - document ambiguous
    - annotator slip
    - genuine disagreement
- **`roles-log.csv`:** participant, role, steps, overlaps with, declared connections, note.
- **`limitations.csv`:** found by (author, annotator, coverage check), document, item, what could not be
  represented, where (guidelines, gold format, GUPI v1, v2 proposal, schema), example, severity, proposal.
  - **Severities:**
    - blocks a question
    - loses detail
    - cosmetic

## Measures reported
See trial-report-template.md, which covers time, usability, consistency (annotator agreement and
disagreements) and representational limitations.

All are descriptive. With six questions and roughly 15-25 claims, nothing is compared with a threshold.

## Decision after the trial (owner)
- **Proceed** to the eight-document mini-pilot, with the guidelines revised from the logs, which is
  expected.
- **Repeat the trial** with revised guidelines, if the disagreements show that the statuses, frames,
  standings or gold format cannot be applied consistently.
- **Revise the estimate or scope,** if the measured minutes are far from the estimate (for example more than
  twice), or if limitations block whole question families.

Limitations attributed to GUPI v1 or the v2 proposal become inputs to the formation milestone and to ADR
0009. They do not change the trial's gold.

## Data handling
- Fictional organisations and people only, with no real names, nothing confidential and no personal data.
  The repository is public.
- Trial data is not held-out data, and is never reused in the development or held-out splits.
- P2 and P3 keep their files locally until the freeze.
- The implementer keeps the frozen copies unchanged, and checks them against their hashes.
- The logs, documents, both frozen files and the adjudicated gold are committed with the trial report, under
  `evaluation/m1/trial/`.
