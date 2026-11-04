# Stage 3 scoring (`phase7b-stage3-scorer/1`)

    uv run python -I -m gupi.benchmarks.phase7b.stage3 score --public docs/evaluation/phase-7b/stage-3/public \
        --private <private gold folder> --responses <bundle>/responses --formation --json <private folder>/<run>.json

**Inputs:**
1. the frozen passages (`public/passages.jsonl`, every text hash checked)
2. the raw responses, one `<passage_id>.json` per passage, read exactly as written
3. the private gold (`gold.jsonl`) and categories (`categories.json`)

**How it works:**
- **Deterministic:** it calls no model or network.
- **Formation:** `--formation` runs every candidate through the real candidate store, in a disposable local
  TypeDB 3.14.1 database.
- **The baseline:** `rules:v2.1` is scored the same way, on the same texts.
- **Where results go:** they contain gold, so **they are written to the private folder, never to this
  repository.**

**Responses are never repaired:**
- **Missing or malformed:** a missing file, or invalid JSON, counts as `invalid-model-output` for that passage.
- **Extra files:** listed as `unexpected`.
- **Hashes:** each response file's hash is recorded.

## Matching (inherited from `phase7b-scorer/1`, scoring-specification.md)
- **Exact:**
  - the same passage, an overlapping span and the same claim type
  - every gold role with the same normalised surface (a gold pronoun's stated antecedent also counts)
  - for statements, the same normalised predicate
- **Partial:** some roles agree. These are listed for adjudication.
- **Overlap, unmatched:** listed for adjudication.
- **Unsupported:** no gold assertion overlaps.
- **One-to-one:** each candidate and each gold group is used once. A second exact match is a duplicate.
- **Abstentions:** an extractor outcome overlapping a gold span is an abstention. It is *appropriate* where
  gold marks the assertion inferred, `?`-resolved, ambiguous or not fully representable.

## Metrics (every rate is k / n with a 95% Wilson interval)
| Group | Metric | Denominator |
|---|---|---|
| Extraction quality | precision, recall, F1 | candidates minus duplicates; gold groups with a GUPI type |
| | duplicates, unsupported, partial, missed; abstained and abstained appropriately | counts |
| | field accuracy: claimant, mode, polarity, modality, commitment, time expression, kind and window | exact matches (with a time, for time fields) |
| Evidence integrity | `claimant`, `claimant_kind` | exact matches (with a claimant in gold or candidate, for kind) |
| | `attribution_mode` (direct or reported); `forwarding_origin` (forwarded, and the original sender right) | exact matches; gold-forwarded matches |
| | `independent_corroboration`: a copy withheld as a copy, and nothing else withheld as one | exact matches with a formation status |
| | `temporal`: every time field right | exact matches with a time |
| | `correction_detected`, `correction_kind`, `correction_target`. A `?` gold target must stay unresolved | gold corrections; detected corrections |
| | `uncertainty_preserved`: hedged gold is never made certain | exact matches with hedged gold |
| Pipeline outcomes | extractor outcomes and flags, by kind | counts |
| | validator rejections, kept apart: the **extractor's** (`validation` outcomes) and the **store's** (schema-aware) | counts |
| | formation: formed, review, withheld, rejected; **formation failures** (exceptions) | candidates |
| | **admission disagreements**: an exact match whose formation outcome differs from gold `expected_admission` (a pipeline result, not an extraction error) | listed |
| | duplicate original attestations (a copy, or a duplicate, formed); supersessions recorded during the run (must be 0) | counts |
| By category | recall per declared passage category | gold assertions in the category |

**Never combined:** no single success score is produced. Extraction, validation and formation results stay
separate throughout.

## Severe errors (defined before any evaluation run)
| Error | Definition |
|---|---|
| invented entity | a participant not in the text, or not a referent of the gold assertion |
| pronoun admitted as a participant | a pronoun kept as a named participant |
| invented assertion | a candidate on a passage whose gold has no assertion |
| unsupported claim | a candidate that matches and overlaps no gold assertion |
| unsupported certainty | `certain` or `direct` where gold is hedged, reported, rumour or an allegation |
| invented time | a date window where gold justifies none |
| false independent corroboration | a repeat or forward presented as a first-hand attestation |
| forwarded presented as first-hand | gold `forwarded`, the candidate `direct` or `reported` |
| invented claimant | a claimant where gold has none (the author asserts it) |
| misattributed claimant | a claimant other than gold's original claimant |
| invented claimant kind | `person` or `organisation` where gold says `unknown`, or the other kind |
| guessed correction target | a correction target where gold says it is not established |
| correction formed without review | a correction, retraction or update formed automatically |
| correction applied automatically | any supersession recorded during the run |
| inference formed | a candidate formed automatically for an assertion gold marks inferred |
| unsupported definitive assertion | a certain claim formed automatically that matches no gold assertion exactly |

**Each severe error lists** its passage, candidate, gold id and formation status. `formed` counts the severe
errors that were admitted without review. The stopping and adoption rules of success-criteria.md (H1–H3)
apply to these counts.

## Adjudication (after scoring; the only way gold can change)
- **What is adjudicated:** the partial and overlapping matches.
- **Who decides:** a person who did not write the gold (not the developer, and not Claude) marks each one
  *equivalent*, *partial* or *different*, with a one-line reason. Only *equivalent* counts as a match.
- **Unsupported candidates:** marked *not supported* or *gold omission*. A gold omission is excluded from the
  precision denominator, and recorded.
- **The record:** the decisions go to `adjudication.csv` in the private folder. Any gold change makes a new gold
  version with a new hash. Gold v1 and the first scoring are kept.

## Limits on what the numbers mean
- **The sample:** 32 passages and 39 gold assertions, written by one author with one style.
  - **Intervals:** about ±15 points near 0.5.
  - **Correlation:** assertions within a passage are correlated, so the intervals are optimistic.
- **Rare errors:** zero severe errors in about 40 candidates still leaves a 95% upper bound near 9%.
- **The ceiling:**
  - **Designed abstentions:** 4 gold assertions are designed to be abstained from (inference, or no
    identity). A faithful extractor misses them for recall, appropriately.
  - **A representation limit:** one admission disagreement comes from a known representation limit
    ("former", with no end date).

## Tests
`tests/unit/test_stage3_scoring.py` (15) and `tests/integration/test_stage3_formation.py` (1) use small
synthetic fixtures (`tests/fixtures/stage3_synthetic.py`). They share no passage, name or gold assertion with
the evaluation corpus. **They cover:**
- correct responses
- a false positive on a negative control, unformed and formed
- a false negative
- a duplicate
- a dropped claimant
- an invented claimant and kind
- a wrong kind
- an unresolved correction kept unresolved, and a guessed target
- a forward presented as first-hand
- pipeline separation (store rejections, failures, supersessions, admission disagreements, copies formed)
- missing and malformed responses
- the structural checks
- the bundle
- the transcript audit (outside paths, disallowed tools, rewritten responses, no transcript)
- the manifest (hashes only)
- real formation
