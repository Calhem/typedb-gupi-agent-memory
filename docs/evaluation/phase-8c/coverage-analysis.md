# Extraction coverage: what is excluded, and where

**How this was measured.** Two ways, on development data only:
- **Best-case probes:** the best possible reply for each construct, on invented messages, through the real parser and policy
  ([results](results/8c-coverage-after-parser-fix.json)).
- **A full manual pass:** every one of the 788 turns of `conv-26` and `conv-30`, written blind to the questions by Claude
  Opus 5.5 ([results](results/8c-manual-dev.json)).

**Caution:** the extractor is also the system's builder, and knows the parser. A model without that knowledge would probably
lose more. These are not independently verified: 100 formed claims are sampled privately for someone else to judge.

## Where 279 assertions went
| Outcome | Assertions | Would have linked two things | Origin |
|---|---:|---:|---|
| **Formed** | **123** (44%) | 5 | |
| Stopped: another pronoun or vague phrase ("it", "they") | 25 | 2 | identity resolution |
| Stopped: no stated subject ("Went to Oslo") | 27 | 2 | parsing |
| Stopped: "my" or "our" ("my kids") | 26 | 2 | identity resolution |
| Stopped: "we" | 19 | 2 | identity resolution |
| Withheld: a dated event | 22 | 1 | formation policy |
| Withheld: a plan or hypothetical | 19 | 0 | formation policy, **correct** |
| Held for review | 12 | 4 | formation policy, **correct** |
| Stopped: conflicts with its own wording | 4 | 0 | parsing, **correct** |
| Stopped: declared as inferred | 2 | 1 | extraction policy, **correct** |

224 of 788 turns (28%) had anything to extract. 111 (14%) ended with a claim.

**The most important column is the third.** Even if every stop were removed, only about 19 assertions of 279 would link two
things. **Sparse links are mainly a property of the conversations, not of the rules.** Across 788 turns the extractor found
22 distinct named participants. People talk about "pottery" and "the adoption agency", which the contract rightly keeps as
descriptive text.

## By construct
| Construct | Best-case result | Origin | In development turns |
|---|---|---|---|
| "I work at Meridian" | **formed, links** | | 47% of turns use "I" |
| "I" inside "Italy", or twice | was stopped; **now formed** | parsing bug, fixed | 12% |
| "I volunteer at a shelter" | formed, **no link** | by design | most formed claims |
| "My sister moved to Oslo" | stopped | identity resolution | 3% name a relation; 28% use "my" |
| "My sister Kate moved to Oslo", the move | formed | | |
| The same, the kinship | **stopped, cannot be expressed** | parsing | |
| "I report to Dana" | formed, links | | |
| "My manager Dana" | stopped | identity resolution | |
| An event with no date | formed | | |
| An event with any date, **even an exact day** | **withheld** | formation policy | 26% have a past action; 11% relative time |
| "She works there", across turns | stopped, **correct** | identity resolution | 49% start with a pronoun |
| "At Meridian." as an answer | stopped | parsing | |
| "Went to Oslo" | stopped | parsing | 57% start with a fragment word |
| "I loved it" | stopped, **correct** | identity resolution | |

Pattern shares are rough word matches, not parsed grammar.

**Protections hold:** hedges go to review; plans, negations, declared inferences and pronouns stop.

## Proposed improvements
Each needs the owner's decision, except P1, which is done. None removes a protection.

| | Change | Recovers | Risk | Recommendation |
|---|---|---|---|---:|
| **P1** | whole-word participant matching | up to 12% of turns could have hit this | none: Stage 3B's replies are identical by hash | **done** |
| **P2** | "My sister Kate": allow `my` as the author, only in a stated relation to a **named** person, in the author's own direct words | the kinship link itself | low: mirrors "I" | **do** |
| **P3** | "my kids" as a descriptor referent, anchored to the author, labelled as written, tier `qualified` | up to 26, and the same thing across sessions | medium: two sisters could share one referent, so never `accepted` | **do, after P2** |
| **P4** | event claims, as Phase 8A option C: additive migration, own time window, never in spell assembly | 22, and dated facts | low: fills a slot the schema left open | **do** |
| **P5** | implicit author for a verb-initial fragment, verified by code, tier `qualified` | up to 27 | medium: an inference, so it can't be `accepted` | decide |
| | Keep stopped: other pronouns, "we", plans, inference | | weakening these is how false memories start | **no change** |

**Why P3 and P4 matter more than their counts.** The P3 referent is the same across sessions, and P4 keeps dates. Together they
add structure the graph doesn't have today. Neither has been built, so neither has been measured.

**Regression tests:** `test_model_candidate.py` covers P1. `test_known_exclusions_stay_visible…` fails if any excluded
construct changes, and `test_protections_hold_on_every_probe` fails if a protection is relaxed.
