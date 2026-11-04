# Candidate contract audit (`gupi.candidate/1`, as implemented on main `0d3ca00`)

**What was read:**
- **Source:** `gupi/formation/candidate.py`, `validate.py`, `rules_v21.py`, `form.py`, `store.py`,
  `qualification.py`, `gupi/timeexpr.py`, and schema `core/0003`, `0010`–`0012`.
- **Live check:** behaviour was checked on a disposable database where noted. Nothing was changed.

**What the "model may populate" column means:**
- **yes:** the model can supply the value, and deterministic code then checks it.
- **no:** code must compute it.
- **text only:** the model copies text, and code derives the value from it.

## Candidate set
| Field | Meaning | Required | Valid values / constraints | In the text? | Interpretation? | Model may populate | Deterministic check | When unknown |
|---|---|---|---|---|---|---|---|---|
| `ir_version` | contract version | yes | `"gupi.candidate/1"` | no | no | **no** | equality | invalid |
| `observation_id` | the observation the set is about | yes | must equal the observation's id | no | no | **no** | equality | invalid |
| `content_hash` | hash of the observation text | yes | `ids.content_hash(text)` | no | no | **no** | equality | invalid |
| `extractor` | method, e.g. `rules:v2.1` | yes | non-empty | no | no | **no** (set by the extractor code) | non-empty | invalid |
| `candidates` | the proposals | no (may be empty) | unique ids | — | — | yes | duplicates rejected | empty set |

## Candidate
| Field | Meaning | Required | Valid values / constraints | In the text? | Interpretation? | Model may populate | Deterministic check | When unknown |
|---|---|---|---|---|---|---|---|---|
| `claim_type` | the relation | yes | lowercase label; with a schema: `employment`, `reporting`, `statement` (`identity` refused) | partly | **yes** | yes | label regex; schema check (see Defect C1) | no candidate |
| `passage.{start,end,text}` | the exact source span | yes | `text == content[start:end]` | **yes** | no | **text only**: code locates it | exact equality | invalid |
| `participants[].role` | role name | yes, at least 1 | label; schema roles of the type | no | **yes** | yes | label; schema | invalid |
| `participants[].surface, start, end` | the player as written | yes | `text[start:end] == surface`, inside the passage | **yes** | no | **text only** | exact equality | invalid |
| `participants[].kind` | referent type | yes | `person`, `organization`, `unclassified` (schema-checked per role) | sometimes | **yes** | yes | enum; schema player kinds | `unclassified` |
| `values[]` | typed attributes, e.g. `job-title` | no | label + non-empty text; schema attributes of the type | yes (text) | some | yes, text only | label; schema (see C1) | omitted |
| `times[].kind` | what the time says | per time | `start`, `end`, `holds-since`, `holds-at` (each of the first three at most once) | partly | **yes** | yes | enum; a "since …" phrase may not be a `start` (`since-as-start`) | omitted |
| `times[].phrase, start, end` | the time text | per time | exact substring inside the passage | **yes** | no | **text only** | exact equality | — |
| `times[].earliest, latest, precision, explicit, assumption` | the window read from the phrase | per time | read by `gupi.timeexpr` against the observation time; `precision` in instant/day/month/year/unknown; unread → no window, precision `unknown` | no | yes (by rule) | **no** | `timeexpr` is deterministic; window order checked | no window, `unknown` (formation sends it to review) |
| `polarity` | asserts or denies | yes | `positive`, `negative` | yes (negation) | some | yes | enum | `positive`, a **risky default** |
| `modality` | actual or not | yes | actual, planned, required, permitted, requested, conditional, hypothetical, question | yes (cues) | **yes** | yes | enum | `actual`, a **risky default** |
| `commitment` | the source's certainty | yes | certain, probable, possible, unknown | yes (hedges) | **yes** | yes | enum | `certain`, a **risky default** |
| `attribution.asserted_by` | the original claimant, if not the author | no | a surface or referent id | yes | some | yes, text only (must occur in the passage, see C3) | **none today** | None: the author |
| `attribution.mode` | how it reached the source | yes | direct, reported, quoted, forwarded, rumour, unattributed | yes (cues) | **yes** | yes | enum | `direct`, a **risky default** |
| `attribution.via` | intermediaries, nearest first | no | ids (rules:v2 puts the author here) | partly | yes | yes, text only | none | empty |
| `attribution.transmission` | how it was transmitted | no | forwarded, transcribed, paraphrased, excerpted, authenticity-unclear | partly | yes | yes | enum | empty |
| `relations[]` | bears on another candidate or claim | no | kind in corrects, retracts, updates, repeats, resumes, contradicts; `marked` stated or inferred; target is a candidate in the set, or a `claim:` / `candidate:` id | partly (cue) | **yes** (target) | the kind and cue: yes; the target: **no** (code resolves it) | enum; target exists | no relation |
| `basis` | stated or concluded | yes | `explicit`, `inferred` | — | — | yes | enum | `explicit`, a **risky default** |
| `confidence` | the extractor's own confidence | no | float 0–1 | no | — | **no** (uncalibrated; never used for admission) | range | None |
| `id` | content hash of all the above | derived | `stable_id("candidate", IR, …)` | no | no | **no** | recomputed when reading the store (tamper check) | — |

## What happens downstream (formation:v1, the candidate store)
| Step | Behaviour | Relevant to a model extractor |
|---|---|---|
| validation in `store.submit` | `validate(cset, observation, schema=None)` **by default: no schema checks** (claim types, roles, kinds, attributes) | the model path must pass the live schema (and C1 must be resolved first) |
| `decide` | rejected if invalid; **withheld** if modality ≠ actual, or a forwarded or quoted copy, or a valid time that cannot be expressed; **review** if commitment ≠ certain, a rumour, a stated or cued correction, or an unread time; otherwise **formed** by the policy | a direct, certain, actual candidate is formed **without review**: false certainty from a model becomes accepted memory |
| `_claim` | participants → referents by `referent_id(scope, kind, surface)` (same surface + kind + scope → same referent); "I" → the author; `asserted_by` → a referent **always of kind person** | same-name merging within a scope (S8); organisational claimants become people (C2) |
| corrections | a suggestion lists target claims (resolved, missing or ambiguous); **nothing is superseded** | safe by design: a model cannot retract anything |
| repeats / forwarded | `repeats` → withheld; forward-copy detection by passage text across messages | forwarded copies cannot corroborate |
| qualification (v2 answers) | standing from commitment, mode and asserter; independence counts distinct originators | the answer side already discounts non-direct evidence |

## Findings that affect a fair experiment
| Id | Finding | Evidence | Consequence |
|---|---|---|---|
| **C1** | **Schema-aware validation rejects every generic `statement` candidate.** `SchemaInfo.load` removes `predicate-text` and `object-text` (they are in `CORE_CLAIM_ATTRIBUTES`), so `validate(…, schema)` reports "statement has no attribute 'predicate-text'". Without a schema, the same candidate is stored and formed. | a disposable-database probe on 2026-11-04 (the reproduction is in model-extractor-design.md, "contract preconditions") | Out-of-domain facts can only be represented as statements, so they would be either all rejected (with schema) or unchecked (without). A correctness defect in the contract; **needs a fix and a test before Stage 2**. Not changed here. |
| **C2** | The asserter referent is always created as a person (known issue). "According to Reuters, …" makes "Reuters" a person. | `form._claim`; the same probe | Attribution to organisations is misrepresented. Score attribution on surfaces, and record kind errors separately. |
| **C3** | `asserted_by` is not checked against the passage text | `validate` has no rule for it | A model could invent a claimant. The model path must check it as an exact substring (the design does). |
| **C4** | **No representation for allegations, disputes or investigations as such.** The nearest are mode `reported` plus commitment `possible` or `unknown`, or the relation `contradicts`. | the enums above | "X is alleged to have …" loses the allegation semantics; score it as a representation gap, not a model error. |
| **C5** | **Only employment and reporting are typed.** Ownership, control, board roles, investigations and decisions are `statement` only (free-text predicate, no constraints). | the schema | Out-of-domain coverage can be measured, but statements are weakly typed, so they are scored on participants and predicate text. |
| **C6** | **Ambiguous identity has no field.** A participant is a surface; resolution is by exact name in scope; identity claims are not extractable. | `_claim`, `_schema` | Identity ambiguity must be annotated and reported by the extractor (an `ambiguous-reference` outcome), not encoded in candidates. |
| **C7** | **Approximate times** ("around 2019", "early in the year") and some relative dates are unread by `timeexpr` or read with an assumption | `timeexpr` | They are kept as phrases with precision `unknown` and sent to review; score whether the phrase is preserved. |
| **C8** | Defaults (`positive`, `actual`, `certain`, `direct`, `explicit`) are the *least cautious* values | `Candidate` defaults | A model that omits a field would silently assert certainty. The model output must state every one of these explicitly. |

## Fields to generate deterministically, never by the model
`ir_version`, `observation_id`, `content_hash`, `extractor`, every offset (`passage.start/end`,
`participants[].start/end`, `times[].start/end`), every time window (`earliest`, `latest`, `precision`,
`explicit`, `assumption`), relation **targets** (code resolves a stated correction against earlier candidates
and the store), `confidence` (left empty), and `id`.
