# Stage 3 gold annotation contract (`gupi.stage3-gold/1`)

**What this is:** how the Stage 3 gold is written. **The gold itself is not in this repository**
(isolation.md). This file says what each gold assertion records and the rules applied. It gives no answers.

## The base: the Phase 7B annotation guidelines
- **Fields and rules:** every gold assertion has the 34 fields of `annotation-guidelines.md` §3, with the
  same meanings. The rules for literal versus inferred readings (§2), ambiguity (§4) and expected admission
  (§5) also apply.
- **The one addition:** `original_claimant_kind`, which is `person`, `organisation` or `unknown`. It is
  required when `original_claimant` is set, and blank otherwise.
- **The check:** `stage3.check_gold` enforces the structure. It reuses `annotations.check_assertions`, and adds
  the kind rule.

## What the brief asks for, and where each one is recorded
| Item | Field(s) |
|---|---|
| subject and predicate | `participants` (subject, or the typed roles), `predicate` |
| object or value | `participants` (object), `title`. A non-entity object is not scored |
| original claimant, and its kind | `original_claimant`, `original_claimant_kind` |
| direct or reported | `attribution_mode` |
| forwarding provenance | `attribution_mode = forwarded`, `attribution_chain`, `independent_origin` |
| polarity, modality, uncertainty | `polarity`, `modality`, `commitment`, `allegation` |
| temporal qualification | `time_expression`, `time_kind`, `time_earliest`, `time_latest`, `time_precision`, `time_basis` |
| correction or retraction | `relation_to_earlier` (corrects, retracts, updates, contradicts, repeats) |
| correction target, including unresolved | `target_assertion_id`: an assertion id, or `?` when the passage does not establish one |
| formed, reviewed or rejected | `expected_admission`: `formed`, `review`, `withheld` or `not-extractable` |
| supporting span | `span_text`, `span_occurrence` |
| stated, inferred or unknown | `literal_or_inferred`, `resolution` (`?` = unknown), `representable`, `representation_gap` |

## Stated, inferred and unknown
- **Stated:** `literal_or_inferred = literal`. Only such assertions may have `expected_admission = formed`.
- **Inferred:** `literal_or_inferred = inferred`, for a referent resolved by inference or an employer implied
  by context.
  - **The resolution:** given in `resolution`.
  - **The admission:** never `formed`. It is `review`, or `withheld` when another rule also withholds it.
  - **Abstaining** is scored as appropriate.
- **Unknown:** `resolution = surface=?`, or `target_assertion_id = ?`.
  - **What the gold never requires:** an extractor supplying the missing identity, date or target.

## Stage 3 conventions, applied consistently
1. **Statements:**
   - **Participants:** only named entities are participants. A descriptive object is object text, and is not
     scored.
   - **The predicate:** the shortest verb phrase in the text.
2. **An event on a stated day:** `holds-at` with a day window. Under §5 ("at some point within a period"), it
   is `withheld`.
3. **A denial** ("X denies …") is X's negative assertion of the denied proposition (§1, §3).
4. **A partly representable assertion** follows §5. It is `review` only where the loss would make the stored
   claim misleading. The gap is always stated.
5. **A correction target** is named only when the passage and its thread establish it; otherwise it is `?`.
6. **Independence:**
   - **`no`:** a repeated copy of a forwarded message.
   - **`unclear`:** a second report of the same claimant's statement. That is one originator, not
     corroboration.
   - **`yes`:** a first-hand account.

## Freezing and changes
- **Gold v1:** frozen before any extraction. Its hash is in manifests/stage-3a.json.
- **Changes after an extraction run:** only through adjudication (scoring/README.md). Gold v1 is never
  edited; a change makes a new version with its own hash.
