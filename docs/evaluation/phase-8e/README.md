# Phase 8E: activity memory feasibility

**Exploratory. One development conversation (`conv-30`), read by hand. Not an evaluation, and not a benchmark or leaderboard result. No schema was added.** The questions are
developer-written, and the comparison is circular by construction: the ledger defines what counts as support. It shows what each representation can express.
Counts: [results](results/8e-activity-conv-30.json). The ledger, quotes and per-question rows are private. Activities appear here as opaque ids, and cases are described in general terms.

**Reader:** the builder, in one sitting, having already seen this conversation, without consulting any question or gold answer. **A second reader may disagree.** No inter-reader check has been done.

## 1. What was recorded
| | |
|---|---:|
| Activities identified | 17 (10 for one speaker, 7 for the other) |
| Mentions, each quote verified against its turn and speaker | 81 |
| Clearly the same activity, so used | 73 |
| Kept out: link only probable or unclear | 8 |
| Activities with an ambiguity that blocks safe linking | **5 of 17 (29%)** |
| Relationship established at stated moments | 10 |
| Ended | 4 |
| Contradictory | 1 |
| Not established: plans or events only | 2 |

Each mention is marked as engagement, start, end, past, an event, a plan, or a plain reference, so **an activity, an event involving it, and engagement with it stay separate.**

**After the last session, 13 of 17 are `unknown` and 4 are `ended`. None is reported as ongoing.** That's correct: silence says nothing.

## 2. The two representations
| | A. Existing claims and events | B. Temporary activity and engagement model |
|---|---|---|
| **History captured** | 33 of 73 mentions have a formed claim (45%); 5 of 8 boundaries | all 73, by hand |
| **Person to activity** | no: the activity is only text | yes |
| **Is it still going?** | **cannot be asked.** All subject-only statements by one person share a proposition key, and an activity spreads across many predicates, so no spell forms | yes, using the unchanged classifier |
| **Events tied to an activity** | only by text | yes |
| **Periods and ends** | only for employment with a named employer; one job here has no formed claim at all | yes, with stated ends |
| **Corrections** | existing supersession | a mention replaces another, with history kept (tested on invented data) |
| **Provenance** | full, per claim | full: the deciding quotes are named |
| **Temporal correctness** | safe, because it says nothing | safe, with one gap: see section 4 |
| **Identity ambiguity** | none, because nothing is linked | **the new risk**: 5 of 17 activities |
| **Automation** | exists | **doesn't exist.** The ledger needed a whole-conversation reading |
| **Complexity** | none | about 280 lines for the test; a real version needs schema, parser and a consolidation step |

**Repeated words are not a usable shortcut.** Using the best word match on today's claims, restricted to the same speaker, **31 of 58 matches (53%) land on another activity or on none.**

## 3. Where the activity model adds something
| Case | Today | With the model |
|---|---|---|
| **"Accepted" is not "started"** (G7) | a text line | event recorded, engagement `unknown`: it never says she began |
| **Same word, different things** (J1, J2; G4, G5) | merged by any word search | a business, a practice and a past competitive habit stay apart |
| **Entering versus hosting** (J6, J7) | one word match | two activities, with a possible link recorded and not made |
| **Plans that never resolve** (J7, and the opening in J1) | a plan is withheld, so it disappears | kept as plans, with no outcome claimed |
| **Over, with no date** (G5, G6) | stopped or text | `ended` by the time it was said, with no invented date |
| **A stated end** (J3, G3) | J3 has no formed claim | `ended`, and stays so, as a default |
| **Still going?** (13 activities) | the reader must infer it | `unknown`, plus the date of the last evidence |

**The honest limit on these.** On "still going?", much of the benefit is discipline, not knowledge: raw text sorted by date would show the last mention, too.

## 4. Where it introduces ambiguity or false continuity
| Case | The risk |
|---|---|
| **J1o: a contradiction** | Direct statements that something is running sit between statements that it hasn't opened. The classifier reads separate moments and **never says contested**. A plain timeline would tell a false story: opened, closed, opened. I had to add a separate check to catch it |
| **J1 and J1o are one reader's choice** | Separating "building it" from "operating it" came from noticing that contradiction across the whole conversation. **That needs hindsight.** A per-message extractor can't do it |
| **G1 and G2: one thing or two?** | Two descriptions of something similar, and later references could be either. Merging would invent a history; splitting may invent a second business. Left unlinked, and 2 mentions are lost |
| **G6: a resumption?** | A past habit, then one recent event. It looks like a return. Nothing states it, so it's recorded as not linked |
| **J6 and J7** | Possibly the same or different. Left apart |
| **Sub-activities** (J8 within J1) | No rule yet for whether one activity contains another |
| **Stable interests look like nothing** (G4) | Repeated present-tense statements, no stated start, so `unknown` between them. That's correct, and it under-reports a lifelong interest |

**A naive "mentioned, so ongoing" reading would have called all 13 `unknown` activities current.** That's the false continuity this design avoids, and the 4 ended ones are the reverse risk.

## 5. Temporal integrity
States come from the unchanged `answering_v2.classify`.
| State | How it arises | Real data | Tested |
|---|---|---|---|
| Confirmed | a statement, at its own moment only | yes | yes |
| Presumed | between a stated start and later evidence, or a stated end | yes, 2 activities | yes |
| Unknown | everything else, including between two mentions | **most** | yes |
| Ended | a stated end, as a default | 4 activities | yes |
| Resumed | a stated restart after a stated end only | **none here** | **invented data only** |

**Mentioned twice is not a period.** With no stated start, the interval between mentions stays `unknown`. Silence never gives completion, abandonment or continuation. The prototype also keeps "true at that time" separate from "known at that time", after a test caught me mixing them.

## 6. Exploratory questions
34 developer-written questions of six types. Turns the ledger marks as support:
| Type | Questions | Support turns | Raw top 10 | Raw top 100 | Word match on claims |
|---|---:|---:|---:|---:|---:|
| What is this person involved in? | 2 | 30 | 1 | 10 | 14 |
| When did it begin? | 6 | 3 | 2 | 3 | 1 |
| Still involved? | 8 | 36 | 14 | 35 | 16 |
| What changed? | 6 | 41 | 13 | 37 | 16 |
| Which events relate? | 6 | 7 | 0 | 4 | 3 |
| What evidence supports it? | 6 | 41 | 14 | 32 | 16 |

The model returns every support turn **because the ledger defines them**, so that isn't a result. What the table does show:
- **At depth 100, raw retrieval already reaches most evidence** for "still?" and "what changed?" on this short conversation. **This is about reading evidence, not finding it.**
- **Raw retrieval is weak for "involved in?" and "which events?",** even at depth 100, because those questions share few words with their evidence.
- **At depth 10, raw retrieval reaches about a third.** A tight budget is where a compact representation could matter.

## 7. Date parser (separate change, `2686597`)
"Last Friday" and "last weekend" are read only where one reading exists, under both Monday-start and Sunday-start weeks. 28 new tests cover month, year and leap-day transitions, and rejection. 5 of 10 stuck development
review items now form; the others stay unread because they really are ambiguous on that date. Results stay marked `derived`. Stage 3B's replies are identical by hash.

## 8. Proposed minimal schema, if justified
**Not implemented, and not yet justified.** If the conditions below are met, this is the smallest version:
```
entity activity sub referent;                       # one person's; label as written; never merged by similarity
relation engagement sub claim,                      # a state: reuses spells as they are
    relates participant, relates activity;
activity plays engagement:activity, plays event-statement:object;
```
One migration, additive. No change to `classify`. **But the schema isn't the hard part.** The extraction contract needs a new relation, and linking needs a **whole-conversation consolidation step** with a human-review path. That's the real cost, and today's per-message design can't do it.

## 9. Recommendation: revise
**Don't implement yet, and don't abandon.**

The model does capture meaningful, temporally qualified relationships GUPI misses: it separates plans, events and engagement, keeps ends, and declines to claim continuity. On that half of the decision, the answer is yes.

On the other half, **"without speculative memory" holds only because a careful reader made 81 judgement calls with the whole conversation in view.** 29% of activities had a blocking ambiguity, and the worst contradiction needed a check that the temporal model doesn't provide. Nothing yet shows that this can be done reliably, or by a machine.

**Three free tests before any schema:**
1. **Second reader.** Someone, or a fresh session that hasn't seen this ledger, reads the same conversation. **If they don't substantially agree on which mentions are the same activity, stop.**
2. **Automated consolidation.** Can a session reading one whole conversation produce the ledger, with no hindsight from me? This decides whether it can ever run unattended.
3. **Answers.** The independent pack's `activity` category, under the [8D protocol](../phase-8d/evaluation-protocol.md), stays the real test. It remains a separate pending workstream.

**Worth adopting regardless of the outcome:** the unreconciled check. Any state-shaped claim that flips without a stated boundary should be flagged. It's small, and it closes a real gap, including for employment. It isn't in this phase's scope, so it needs your approval.
