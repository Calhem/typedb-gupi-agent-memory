# Spreadsheet annotation template (draft v0)

Date: 2026-11-03. Status: **provisional**, like the guidelines it follows (guidelines-v0.md, revision 2).

**What it is.** A way to annotate in an ordinary spreadsheet (LibreOffice, Excel, Google Sheets, Numbers)
instead of writing JSON by hand. It is not an application: there is no user interface.

**The canonical format** is still JSON Lines (guidelines §15). The sheets are a convenient way to write it,
and they convert to it by the fixed rules below. Where they disagree, the JSON Lines definition wins.

## How to use it
1. Copy this folder for each annotator, and work in your copy only.
2. Open the CSV files as sheets of one workbook, one sheet per file, with the sheet name equal to the file
   name. Keep the header row exactly as given.
3. Fill one row per record. Leave a cell empty when the field does not apply.
4. Optionally, add drop-down lists (data validation) for the columns whose allowed values are listed below.
5. When you finish, save each sheet back as CSV (UTF-8, comma-separated), then freeze by hash as described
   in the trial README.

## Conventions
- **Ids** are short strings with the guidelines' prefixes (`seg-`, `ent-`, `st-`, ...). Each id is unique
  within its sheet.
- **Lists in one cell** are separated by `;` with no spaces around it, for example `ent-ravi;ent-wen`.
- **Spans** are written `start-end`, and several spans `12-80;95-120`. Offsets count characters from 0, and
  the end is exclusive.
- **Dates** are ISO 8601 (`2026-04-20`). Time ranges use the two columns `value_from` (inclusive) and
  `value_to` (exclusive).
- **Times referenced from other sheets** (`written`, `event_time`, `holds_from`, ...) are ids of rows in
  `times`.
- **Text** may contain commas: spreadsheet programs quote such cells automatically when saving CSV.
- **Empty cell** means the field is absent. Never write `none`, `n/a` or `-` unless that is a listed value.

## Sheets
| Sheet | One row per | Notes |
|---|---|---|
| `documents` | document | |
| `segments` | message or section | `relation`: original, reply-to, quote-of, forward-of; `related` is a segment id |
| `entities` | entity | `aliases` is a `;` list |
| `mentions` | mention | `reference`: name, pronoun, role-reference, description; `resolved`: stated, inferred, unresolved |
| `times` | time expression | `anchor`: explicit, document-date, other-time, inferred, unresolvable |
| `statements` | statement | allowed values below; `holds_at`, `via` and `transmission` are `;` lists |
| `participants` | participant of a statement or judgement | `owner` is the statement's or judgement's id; `filler_kind`: entity, time, value, statement; `filler` is an id, or the literal value |
| `links` | link | `type` and `marked` as in guidelines §11 |
| `judgements` | judgement | `based_on`, `against` and `inference` are `;` lists; participants go in `participants` |
| `questions` | question | `about_time` is the question's own wording of the time; `about_from` and `about_to` give its range; `mode`: at, throughout, at-some-time; `frame`: recorded, actual, unspecified |
| `answers` | answer (one per frame) | `value_forms` and `inference` are `;` lists |
| `answer_evidence` | evidence item | `kind`: essential, context, counter. `set` is a number grouping essential items into sets (1, 2, ...); empty for context and counter items. `side` is used only for disputed answers. |
| `answer_sides` | side of a disputed answer | `side` is a short label (A, B, ...) matching `answer_evidence.side` |
| `answer_alternatives` | alternative answer | `alt` numbers them within the answer |
| `rejected_candidates` | rejected candidate | `reason` as in guidelines §13.3 |
| `adjudication` | adjudicated difference | `items` is a `;` list of the two annotators' record ids |

## Allowed values (for drop-down lists)
| Column | Values |
|---|---|
| `statements.kind`, `judgements.kind` | state, event, decision, obligation, other |
| `statements.polarity` | affirmed, negated |
| `statements.conveyed` | stated, implied |
| `statements.commitment` | certain, probable, possible, unknown |
| `statements.modality` | actual, planned, required, permitted, requested, conditional, hypothetical, question |
| `statements.attribution` | direct, reported, quoted, forwarded, rumour, unattributed |
| `statements.standing` | authoritative-record, direct-observation, reported, plan, unverified |
| `statements.transmission` (a `;` list) | forwarded, transcribed, paraphrased, excerpted, authenticity-unclear |
| `links.type` | corroborates, contradicts, corrects, retracts, updates, refines, repeats, resumes, fulfils, cancels, depends-on, doubts |
| `links.marked` | stated, inferred |
| `judgements.belief` | happened, did-not-happen, uncertain, sources-disagree |
| `judgements.reasoning` | taken-from-source, inferred |
| `answers.status`, `answer_alternatives.status` | stated, inferred, disputed, insufficient, not-yet-available |
| `answers.ambiguity` | none, wording, evidence, frame |
| `inference` (any sheet) | continuation, combination, date-calculation, reference, consequence, closed-list, other |
| `confidence` (any sheet) | high, medium, low |
| `adjudication.outcome` | a-correct, b-correct, both-acceptable, merged, unresolvable |
| `adjudication.cause` | guideline unclear, guideline silent, document ambiguous, annotator slip, genuine disagreement |

## Conversion to JSON Lines (canonical)
The conversion is mechanical and loses nothing. Each rule is fixed, so two people converting the same sheets
get identical files.
1. **Rows become records.** Each row of a record sheet becomes one JSON object with `"record"` set to the
   singular sheet name: `document`, `segment`, `entity`, `mention`, `time`, `statement`, `link`,
   `judgement`, `question`, `answer` or `adjudication`.
   - Empty cells are left out.
   - Numbers in `start` and `end` become integers.
2. **Lists:** cells holding `;` lists become JSON arrays. Spans become arrays of `[start, end]` pairs.
3. **Grouped fields:**
   - `value_from` and `value_to` become `value: {from, to}`.
   - `about_from`, `about_to` and `mode` become `about_time: {from, to, mode, text}`, with `text` taken from
     the `about_time` column.
   - `value_text`, `value_entity` and `value_forms` become `value: {text, entity, forms}`.
4. **Child sheets are folded into their owner,** in row order:
   - `participants` rows into their owner's `participants`
   - `answer_evidence` rows:
     - `kind` essential into `evidence`, one inner list per `set` number, in ascending order
     - `kind` context into `context`
     - `kind` counter into `counter_evidence`
   - `answer_sides` into `sides`
   - `answer_alternatives` into `alternatives`
   - `rejected_candidates` into `rejected_candidates`
5. **Output files:**
   - the source-layer sheets become `<document>.<annotator>.jsonl` (one file per document, by each row's
     document or segment)
   - entities, judgements, and links between statements in different documents become
     `shared.<annotator>.jsonl`
   - questions become `questions.jsonl`
   - answers become `answers.<annotator>.jsonl`
   - adjudication becomes `adjudication.jsonl`
   - Within a file, records appear in sheet order, then row order. The order of record rows across documents carries no
     information, and is not preserved. Child rows keep their order within their owner.
6. **Checks during conversion:**
   - every referenced id exists
   - every enumerated value is allowed
   - every essential evidence item has a set number
   - a disputed answer has at least two sides

   Errors are listed, and nothing is guessed.

**The converter** is `scripts/annotation_export.py` (standard library only):

    python -I scripts/annotation_export.py <sheets folder> <output folder> --annotator <name>

It applies these rules, plus a reverse conversion, and refuses to write anything unless the sheets pass
every check and the round trip loses nothing. It also checks each mention's and time's text against the
document at its offsets, when the document files are present. The dry check (../dry-check/) shows it on the
guidelines' examples.
