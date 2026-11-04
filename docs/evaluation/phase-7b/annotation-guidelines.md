# Gold annotation guidelines (Phase 7B)

These guidelines are for independent annotators. They describe what the **source says**, not what any
extractor or GUPI does. The templates are in `annotation-templates/`. Check your files with:

    uv run python -I -m gupi.benchmarks.phase7b.annotations check <folder>

The checker verifies structure only (spans occur in the text, values are allowed, ids are consistent). It
never judges content.

## 1. The unit: an assertion
- **What an assertion is:** one relationship or state that the passage *puts forward as information*,
  whether as fact, report, allegation, plan, hypothetical or denial.
- **One assertion per proposition per statement:**
  - **Merging:** if the same sentence says it twice, it is one assertion.
  - **Separate statements:** if two people state it, there are two assertions.
- **What is not an assertion:**
  - questions
  - greetings
  - an opinion with no factual content ("great news!")
  - instructions
  - quoted material the author explicitly rejects ("the claim that X is false" is a *negative* assertion by
    the author; the rejected claim is recorded only as the claimant's assertion)
- **Negative controls:** a passage with no assertion gets none, and that is a valid gold result.

## 2. Literal meaning versus inference
**Every field records the literal meaning first.**
- **When an inference is needed** (resolving "she" to a person named earlier; reading "our CFO" as the
  author's company): set `literal_or_inferred = inferred` and explain it in `notes`.
- **What is never done:** completing a missing name, date or organisation from world knowledge.

## 3. Fields (annotation-templates/assertions.csv)
| Field | Rule |
|---|---|
| `assertion_id` | unique, e.g. `S1-007-a3` |
| `passage_id` | as in passages.csv |
| `span_text` | the **exact** text of the smallest span that states it (copy, never retype). Must occur in the passage. |
| `span_occurrence` | which occurrence, if `span_text` occurs more than once (1 = first) |
| `relation` | a short lowercase label for what is asserted (`employment`, `reporting`, `appointment`, `ownership`, `investigation`, `allegation`, `residence`, …) |
| `gupi_claim_type` | the nearest GUPI type: `employment` (person works for organisation), `reporting` (person reports to person), `statement` (anything else that can be put as subject–predicate–object), or `none` (not representable) |
| `participants` | `role=surface` pairs separated by ` \| `, surfaces exactly as written (e.g. `employee=Mara Quist \| employer=Pellwick`). Roles for typed claims: employee and employer; report and manager. For statements: subject and object. **Do not resolve pronouns here.** Write the pronoun, and give the antecedent in `resolution`. |
| `resolution` | for any pronoun or vague reference in `participants`: `surface=antecedent text` (only if the passage itself makes it unambiguous), otherwise `surface=?` |
| `predicate` | for statements: the predicate in a few words, as close to the text as possible (`owns`, `is investigating`) |
| `title` | a job title or role, if stated (employment) |
| `source_speaker` | who wrote or said the passage (the author or sender), as written, or `author` if unnamed |
| `original_claimant` | who originally made the assertion, if different (e.g. "According to Dana Okoro, …"), as written; otherwise blank |
| `attribution_chain` | intermediaries from the source back to the claimant, nearest first, separated by ` \| ` (e.g. forwarded by X, from Y) |
| `attribution_mode` | `direct` (the speaker asserts it), `reported` ("X told me", "according to"), `quoted` (verbatim quotation), `forwarded` (inside a forwarded message), `rumour` ("I hear", "word is"), `unattributed` ("it is understood that") |
| `independent_origin` | `yes` if this assertion is a fresh observation by its claimant; `no` if it repeats or forwards another assertion in the corpus (give that id in `target_assertion_id`); `unclear` |
| `polarity` | `positive` or `negative` (explicit denial: "is not", "never", "denies") |
| `modality` | `actual`, `planned`, `required`, `permitted`, `requested`, `conditional`, `hypothetical`, `question` |
| `commitment` | the **source's** certainty: `certain`, `probable` ("probably", "I think"), `possible` ("might", "may"), `unknown` |
| `allegation` | `yes` if presented as an allegation or a disputed claim ("alleged", "accused of", "denies"); otherwise `no` |
| `time_expression` | the time words exactly as written (`since March`, `last spring`), or blank |
| `time_kind` | `start`, `end`, `holds-since` (held from then until the statement; **not** a start), `holds-at` (held at the time referred to), or `none` |
| `time_earliest`, `time_latest` | the interval the expression justifies, as ISO dates `[earliest, latest)`, **only if the text plus the document date justify it**; otherwise blank. "since March", said on 2025-08-20 → `holds-since`, earliest blank, latest `2025-04-01` |
| `time_precision` | `day`, `month`, `year`, `approximate`, `relative-unresolved`, `unknown` |
| `time_basis` | `stated` (in the text), `document-date` (resolved using the document's date, e.g. "last month"), `tense-only` (the present tense implies "now"), `none` |
| `relation_to_earlier` | `corrects`, `retracts`, `updates`, `repeats`, `contradicts` or `none` |
| `target_assertion_id` | the earlier assertion it corrects, retracts, updates, repeats or contradicts, if identifiable; `?` if a correction is stated but its target is unclear |
| `literal_or_inferred` | `literal` or `inferred` (see §2) |
| `representable` | `yes` (fits the typed or statement fields above without loss), `partial` (loses something; say what in `representation_gap`), `no` |
| `representation_gap` | what cannot be represented (an allegation, an organisation as claimant, ownership share, identity ambiguity, …) |
| `expected_admission` | what **should** happen to it under GUPI's policy, as stated in §5: `formed`, `review`, `withheld` or `not-extractable` |
| `ambiguity` | blank, or a description of a real ambiguity (then use `alternative_of` too) |
| `alternative_of` | for an alternative reading of an ambiguous assertion: the id of the main reading. Both are gold, and an extractor matching either is correct |
| `notes` | anything else |

## 4. Ambiguity
- **When the passage supports more than one reading:**
  - **Example:** "Dana left the team in May": left the organisation, or only the team?
  - **What to do:** annotate the most literal reading, and add each alternative as its own row with
    `alternative_of`.
- **Do not choose for the extractor.** If you cannot tell, say so in `ambiguity`.
- **When something is under-specified** (a name with no surname, a missing year): record it as written. Do
  not complete it.

## 5. Expected admission (GUPI's current policy, written out so annotators can apply it without code)
| Outcome | When |
|---|---|
| **withheld** | the modality is anything other than actual (a plan, conditional or hypothetical); or the assertion repeats or forwards another one; or its time says only "at some point within a period" |
| **review** | the commitment is not certain; or it is a rumour; or a correction is stated; or a stated time cannot be read as a date range |
| **formed** | otherwise, if it is representable |
| **not-extractable** | `representable = no` |

## 6. Adjudication
1. **Two annotators work independently** on every S1 and S2 passage, without seeing each other's files or any
   extractor output.
2. **The disagreement report** is produced by the checker (`compare <a> <b>`). It matches assertions by
   passage and overlapping span, then lists every field that differs, and assertions only one annotator
   found.
3. **The adjudicator decides** each disagreement and records it in `adjudication.csv`:
   - the item
   - annotator A's value, annotator B's value and the decision
   - a rationale, in one line
   - whether the ambiguity is genuine (→ keep both as alternatives)
4. **Agreement is reported before adjudication,** per field: raw agreement, and Cohen's κ for categorical
   fields with enough items.
5. **The frozen gold** is the adjudicated set. Its hash goes into the manifest before any extractor runs on
   S1 or S2.

## 7. Worked examples (developer-authored, illustration only, not evaluation material)
These examples are written by the developer, so they are **not independent evidence**.

> Passage (email, sent 2025-08-20 by Ivo Marsh): "FYI — Dana Okoro told me Pellwick has appointed Mara Quist
> as interim CFO since last month. Nothing official yet."

| Field | Value |
|---|---|
| span_text | `Pellwick has appointed Mara Quist as interim CFO since last month` |
| gupi_claim_type | `employment` |
| participants | `employee=Mara Quist \| employer=Pellwick` |
| title | `interim CFO` |
| source_speaker | `Ivo Marsh` |
| original_claimant | `Dana Okoro` |
| attribution_mode | `reported` |
| independent_origin | `yes` |
| commitment | `probable` ("Nothing official yet" qualifies it). An annotator may argue `certain` with an ambiguity note. |
| time_expression | `since last month` |
| time_kind | `holds-since` |
| time_latest | `2025-08-01` |
| time_precision | `month` |
| time_basis | `document-date` |
| expected_admission | `review` |
