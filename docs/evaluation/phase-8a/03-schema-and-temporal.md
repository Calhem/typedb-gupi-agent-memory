# Phase 8A, part 3: schema and temporal compatibility

## 1. Schema impact
**8B needs no schema change, no migration and no new data.** Every query in part 2 runs on the current schema.

| Possible change | Needed for | Recommendation |
|---|---|---|
| A concrete event type or mapping (§3) | one-time events entering the claim graph | decide in 8C from measured impact |
| Store possible targets as `correction-suggestion` targets | a pending retraction reaching its claims | no schema change: the role already allows several targets; 8C formation change |
| Persist explicit-versus-inferred on claims | returning that flag without reading candidate JSON | none at first: read from `candidate-payload` via `candidate-id`; revisit if slow |
| A turn-order relation | neighbours | **no:** Q3 reads `observed-at` |
| TypeQL functions | shared patterns | defer (part 2 §5) |

## 2. How temporal semantics are preserved
**One rule carries most of the weight: a path is a list of separately qualified hops, never one fact.**

| Requirement | How it holds |
|---|---|
| Explicit versus inferred dates | hop labels carry precision and bases; the explicit flag comes from the candidate; nothing is recomputed |
| Validity intervals and spells | valid time stays per claim; spells come from `answering_v2`, unchanged |
| Confirmed versus presumed | `classify` keeps TRUE and PRESUMED distinct; PRESUMED puts a hop in tier `qualified` |
| Separate periods, departures, reinstatements | proposition completion (Q6) gives `classify` every claim, so a gap stays a gap |
| Recorded versus valid time | `believed_at` filters by transaction time; `valid_at` is a separate argument, as in `Question` |
| Corrections and provenance | supersessions and reviews come through `claims_by_ids`; superseded claims are listed, not hidden |
| Pending retractions, contradictions | Q7 and tier `unresolved`; a pending retraction changes no answer (tested in Stage 4) |
| Allegations and reports | `commitment`, `attribution-mode` and `assertion` flow through `qualification.qualifiers`; R3 tested this through retrieval |

**Why hops cannot be filtered by claim-level time in TypeQL.** The obvious filter ("drop claims that do not overlap")
is wrong. "Joined in 2021" and "left in 2023" are **two claims**: neither alone covers 2022, and the spell exists
only when they are read together. Filtering either away would lose the spell or the departure. So TypeDB selects by
structure and belief, and time is decided afterwards on the completed proposition.

**How a two-hop label works.** For hops A and B, ask `classify` about A at B's time. If B's time is a window, ask
at both ends:
| Result at both ends | Hop label |
|---|---|
| TRUE at both | `overlap: confirmed` |
| includes PRESUMED | `overlap: presumed` (assumes no unrecorded break) |
| FALSE at both | `overlap: none` |
| anything else | `overlap: unknown` |
| B has no time | `overlap: unknown`, stated, never assumed |

**Measured on the Alice scenario** (real formation, `probes/results-queries.txt`):
| Question | At | Answer | Why this is right |
|---|---|---|---|
| Employed at Meridian? | during 2022 | **PRESUMED** | joined from a start and an end in two claims; "assumes no unrecorded break" |
| | mid 2023 | **UNKNOWN** | inside the year she left |
| | mid 2024 | **FALSE** | recorded as ended, stated as a default |
| Acquisition in effect? (two sources disagree on 2022 and 2023) | mid 2022 or 2023 | **UNKNOWN** | inside the uncertain date; no date preferred |

**A note on disputes.** Here two start dates give UNKNOWN, not CONTESTED: CONTESTED needs claims that decide the date
in opposite directions. Retrieval must therefore show the dispute itself, through Q8 listing both attestations. It
cannot rely on the answer label alone.

## 3. One concrete incompatibility: one-time events
**Finding (confirmed by running it).** "Meridian acquired Northstar in 2022", read as `holds-at`, is **withheld**:
`valid_time` refuses a coarse `holds-at`, because a valid time cannot say "at some instant in this window"
(`validate.py:230`). Stage 3B withheld 4 candidates this way. This is the correct conservative behaviour for a
state, and it keeps such events out of the graph.

**The workaround hides a problem.** If an extractor labels the same phrase `start`, it forms, as a *state* that began
in 2022 with an unknown end. That is not false, because `holds_at` stays UNKNOWN after the window. But it depends on
how the model chose the label, and "the acquisition" is treated as an ongoing condition.

**The schema anticipated this and never finished it.** `event` (`core/0001`) owns `occurred-at-earliest/latest`, but
is abstract with no subtype, and nothing writes those attributes.

| Option | Change | Cost | Temporal risk |
|---|---|---|---|
| A. Leave withheld | none | events stay raw text only | none; recall loss |
| B. Form as a state start | formation policy | smallest | reads events as states; **not recommended** |
| C. Add `event-statement sub event` | migration `core/0013` (additive), formation mapping, one branch in answering | moderate | low: uses the model's own `occurred-at` window; a new claim type must not enter spell assembly |

**Recommendation:** start with A in 8B, measure how many fixture questions fail only for this reason, and take C to
the owner in 8C if the number justifies it. C does not compete with the temporal model: it fills a slot that model
already defined.

## 4. Other limits that bear on retrieval
- **Statement keys ignore predicates** (`records.py:26`). Paths always group by key **and** `predicate-text`. Changing
  the key would change existing ids, so it is not proposed.
- **The "since" issue** (`docs/known-issues.md`) carries through unchanged and is reported, not fixed here.
- **Same-named people in one conversation** (S8): unchanged.
- **`evidence.keyword` has no belief-time filter:** seeds must use the `received-at` condition from `search.py:48`,
  or as-of retrieval would leak later text.
