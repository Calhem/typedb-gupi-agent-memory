# Dry check of the annotation template

Date: 2026-11-03. **Not trial data.** This folder uses only the guidelines' existing fictional Examples 4,
5 and 8 (guidelines-v0.md §16). The trial's documents and questions have not been written.

## What was checked
1. **Coverage:** the examples were annotated in the spreadsheet template. Every one of the 16 sheets holds
   at least one row:
   - 9 documents
   - 12 statements
   - 25 participants
   - 5 questions and 5 answers, including a disputed answer with two sides, an alternative, rejected
     candidates, and essential, context and counter evidence
   - one judgement
   - one illustrative adjudication row
2. **Required fields** can be completed for every record type: the exporter's required-field check passes.
3. **Offsets:** every mention's and time's text equals the document text at its offsets.
4. **Lossless export:** the sheets were exported to JSON Lines (81 records in 13 files, in `jsonl/`), then
   converted back. Every cell of every sheet came back unchanged.
5. **Errors are reported:** a deliberately broken copy is rejected with specific messages. It had:
   - an unknown standing
   - a missing entity
   - a text mismatch
   - a gap in set numbers
   - a disputed answer with one side

Checks 1-5 run as a unit test (`tests/unit/test_annotation_export.py`), so they stay true as the template
changes. To repeat by hand:

    python -I scripts/annotation_export.py docs/specialist/authoring-trial/dry-check/sheets /tmp/out --annotator dry

## Defects found, and what was done
| # | Finding | Action |
|---|---|---|
| D1 | The guidelines said "one file per document", but entities, judgements and links between statements in different documents belong to no single document. | **Fixed:** they go in `shared.<annotator>.jsonl` (guidelines §15; template README). |
| D2 | The order of record rows across documents cannot survive splitting into per-document files. | **Documented:** row order carries no information. Order within an owner (evidence sets, alternatives) is kept. |
| D3 | The guidelines did not say whether a statement's **standing** is judged for its original asserter or for the record as it reaches the reader. | **Resolved by the owner** (guidelines revision 3, §8.1-§8.2): standing describes the underlying assertion and its originating source. The record's limits are tracked separately in `transmission`. The dry check now records Hana's statement as `direct-observation`, transmission `transcribed`. |
| D4 | One phrase ("Joaquín is back as site lead from next Monday") carries two statements: a plan, and an implied current negation. The format allows this (overlapping spans), but the guidelines do not show it. | **Not changed.** It works; the trial will show whether annotators find it. |

## What a dry check cannot show
- Whether a **person** finds the sheets workable, and how long they take. The dry check was filled in by the
  implementer, programmatically, from examples the implementer wrote.
- Whether two people would fill them in the same way.

These are measured in the trial itself (time log, disagreements) and asked of the reviewer.
