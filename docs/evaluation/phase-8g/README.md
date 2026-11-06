# Phase 8G: activity replication and decision

**Recommendation: B. Keep activity consolidation as an experimental tool. Do not implement it.** The rule fixed in advance gives this outcome. The conversation produced clean evidence and useful structure, but final states are not reliable by either route, and reading depth changes the answer.

**Two development conversations, one dataset. No human was involved. Every ledger and judgement came from a Claude model, under one subscription. Agreement is not accuracy. Nothing here is independently validated, and nothing is a benchmark or leaderboard result.**
Numbers: [agreement](results/8g-agreement.json), [verdict](results/8g-verdict.json), [temporal](results/8g-temporal.json), [post-hoc](results/8g-post-hoc.json); first conversation with the control: [agreement](results/8g-control-agreement.json), [temporal](results/8g-control-temporal.json), [post-hoc](results/8g-control-post-hoc.json). Rules: [protocol](protocol.md), frozen at `5b46faf`, amended at `e16d84a` before any score existed.

## Who produced what
| Output | Producer | Conversation | Activities | Mentions |
|---|---|---|---:|---:|
| A | fresh Claude Opus 5.5 session, manual | second | 47 | 196 |
| B | fresh Claude Sonnet 5.5 session, manual | second | 41 | 116 |
| C1 | fresh Claude Sonnet 5.5 session, specification | second | 22 | 79 |
| C2 | fresh Claude Haiku 5.5 session, specification | second | 22 | 84 |
| A-control | fresh Claude Opus 5.5 session, manual | first | 35 | 171 |
| Judges | fresh Opus 5.5 and Sonnet 5.5 sessions, two per conversation | both | | |

**The first run was invalid and was never scored.** All five agents received a cached memory line carrying the 8F conclusion, which the audit found. The rerun's nine sessions were each audited from their transcripts: each read only its own folder, wrote only its own output, ran on the intended model, and received no line about this project.

**Conditions that differ from 8F.** A was the builder session in 8F, and is a fresh agent here. B, C1 and C2 were subagents in 8F, and are full sessions here. Reasoning effort may differ and was not measured. These are real differences, so the conversations are compared side by side and never pooled.

## Replication results
| Criterion | Measure | Threshold | First conversation (8F) | Second conversation |  |
|---|---|---:|---:|---:|---|
| **1. Reproducible** | mention F1, A with B | 0.70 | 0.71 | 0.72 | pass |
| | activity F1 | 0.60 | **0.59** | 0.82 | pass |
| | adjusted Rand | 0.70 | **0.53** | 0.96 | pass |
| | B-cubed F1 | 0.75 | 0.79 | 0.97 | pass |
| **2. Merges, continuity** | merge rate | at most 0.15 | 0.09 | 0.00 | pass |
| | invented continuity | 0 | **1, 1, 1** in B, C1, C2 | **11 in B, 5 in C2**, 0 in A, C1 | **fail** |
| **3. Provenance** | valid evidence | at least 98% | 100% | 100%, 475 of 475 | pass |
| **4. Temporal ambiguity** | final-state kappa | 0.60 | 0.71 | **0.16** | **fail** |
| | shared conflict | present | yes | yes | pass |
| **5. Automation** | C1 mention F1, against A and B | 0.70 | 0.72, 0.76 | **0.55**, 0.76 | **fail** |
| | C1 adjusted Rand | 0.70 | 0.78, 0.78 | 0.87, 0.84 | pass |
| | correction share | at most 0.30 | **0.31**, 0.13 | 0.18, 0.18 | not reached |

**Second conversation: criteria 1 and 3 pass; 2, 4 and 5 do not.** The verdict code reproduces 8F's verdict from 8F's numbers, and a test holds it there.

| Pair, second conversation | Mention F1 | Activity F1 | Adjusted Rand | B-cubed F1 | Role kappa | Link kappa | Written-state kappa | Computed-state kappa |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A, B | 0.72 | 0.82 | 0.96 | 0.97 | 0.79 | 0.30 | 0.16 | 0.79 |
| A, C1 | 0.55 | 0.58 | 0.87 | 0.92 | 0.85 | 0.31 | 0.00 | 0.23 |
| A, C2 | 0.54 | 0.55 | 0.74 | 0.86 | 0.62 | -0.11 | -0.13 | 0.50 |
| B, C1 | 0.76 | 0.63 | 0.84 | 0.91 | 0.70 | 0.35 | 0.00 | 0.14 |
| B, C2 | 0.66 | 0.57 | 0.72 | 0.86 | 0.72 | 0.20 | 0.21 | 0.37 |
| C1, C2 | 0.71 | 0.73 | 0.85 | 0.92 | 0.70 | 0.26 | 0.00 | 0.54 |

**Against what A and B agree on** (a floor, not gold):
| | Agreed mentions recovered | Agreed links recovered (false separations are the rest) | Agreed separations broken (false merges) |
|---|---:|---:|---:|
| C1, second conversation | 71 of 112, 63% | 116 of 177, 66% | 23 of 6,023, 0.4% |
| C2, second conversation | 64 of 112, 57% | 75 of 177, 42% | 37 of 6,023, 0.6% |
| C1, first, in 8F | 43 of 55, 78% | 57 of 76, 75% | 9 of 1,294, 0.7% |
| C2, first, in 8F | 34 of 55, 62% | 38 of 76, 50% | 16 of 1,294, 1.2% |

**Contradictions.** Second conversation: 26 reports, 9 distinct, 7 from at least two ledgers, 2 from all four. First: 24 reports including the control, 3 distinct, all from at least two ledgers.

**Review.** C1 raised 49 items on the second conversation (11.7 per 100 turns) and 35 on the first (9.5). C2 raised 42 and 22. A and B exceed the line, at 20.8 and 16.7.

## Is the classifier right, or merely consistent?
**The agreement gain replicates. The correctness gain does not exist.** Median written kappa against computed kappa: first conversation 0.70 to 0.81, second 0.00 to 0.43.

Blind judges agreed on 88 of 104 cases on the first conversation (kappa 0.78), and only 71 of 132 on the second (kappa 0.27). In 56 of those 132 cases, under the same rule, Opus said unknown and Sonnet said engaged. So the second reference is thin, and tilted to where the stricter judge also said engaged.

| Correct against the judges | Second: written | Second: computed | First: written | First: computed |
|---|---:|---:|---:|---:|
| A | 19 of 26 | 17 of 26 | 8 of 16 | 8 of 16 |
| B | 24 of 26 | 17 of 26 | 18 of 24 | 15 of 24 |
| C1 | 4 of 10 | 5 of 10 | 9 of 15 | 7 of 15 |
| C2 | 4 of 9 | 1 of 9 | 5 of 8 | 3 of 8 |
| A-control | | | 21 of 25 | 14 of 25 |

Written states are ahead or level in eight of nine rows. C1 rises 10 points on the second conversation, but from 0 to 2 wrong-way errors, and falls 13 points on the first. **The frozen test for a genuine gain fails on both conversations.**

**Claims beyond the evidence:** computed states made 8 unsafe or wrong-way errors on the second conversation, and written states made 1. On the first it was 3 against 0.

| Where the gained agreement came from (the six reader pairs) | Second | First |
|---|---:|---:|
| Pairs whose written states differed but computed states matched | 38 | 12 |
| Correct, on shared evidence (genuine) | 2 | 2 |
| Correct by default | 1 | 0 |
| Incorrect | 12 | 6 |
| Undecided | 23 | 4 |

**Why it is mostly mechanical.** Asked a day after the end, the classifier cannot say engaged at all. Nearly everything becomes unknown, and the rest ended, so ledgers converge whatever their evidence. Two fixed behaviours add errors. A `past` mention closes an activity, though readers use it for past-tense statements about things still going. And an undated start with an end stays unknown. **The 8F result, "A with C1 rises from 0.24 to 0.81", was mostly this collapse.**

**One measure failed.** The check at the end itself gave the same figures everywhere, because a statement holds only at its exact moment, so only a mention in the very last turn could count. It tells us nothing.

## Combined assessment
| Question | Answer |
|---|---|
| **Which results replicate?** | Complete evidence. Few false merges. Granularity disagreement. Link certainty not reproducible. Haiku's weaker linking. Classifier agreement without correctness. |
| **Which depend on conversation structure?** | Grouping: A-B adjusted Rand is 0.96 here, 0.53 in 8F, 0.64 with the control. The second conversation has many separate pursuits, and the first has overlapping ones. Final-state agreement goes the other way: 0.16 here, 0.71 in 8F, 0.55 with the control. Ongoing pursuits make "still continues" a matter of reading. |
| **Are boundaries sufficiently reproducible?** | **Separation yes, boundaries no.** Readers rarely join what others separate, but they differ on how many activities exist: 22 to 47 here, 9 to 35 there. Adjusted Rand only scores mentions both readers found, so it flatters this. Activity F1 for C1 against A is 0.58. |
| **Does automation add unsupported memories?** | **Not by fabricated evidence:** every quote checked out, and judges never agreed a case wasn't one activity. **It does overreach:** C2 has 5 invented-continuity cases, 2 confirmed engaged by the judges, 3 undecided. B has 11: 5 confirmed, 6 undecided. These are more contested reading than invention, but they do fail the test. |
| **Quiet merges?** | C1 merged two pairs of similarly named activities and flagged both. **C2 did the same and flagged neither**, repeating its 8F failure. C1's flagging is useful; Haiku's output isn't safe unreviewed. |
| **Is the review burden practical?** | It meets the line I set (C1 at 11.7, under 15). In practice that is 49 decisions for one conversation. Practical for occasional deep review, not routine use. Only the automated ledgers meet it. |
| **Could a minimal index run safely without an engagement schema?** | **Yes for evidence, no for state.** Quotes, proposed groups and review items could be held safely, so long as it asserted no final state. |

**8F's recommendation changes.** I recommended keeping classifier-computed final states. **I withdraw that.** Neither written nor computed states are fit to store. Invented continuity went to zero only because the classifier cannot say engaged.

## Decision
Applying the rule fixed in advance:
| Outcome | Conditions | Result |
|---|---|---:|
| **A. Implement** | criteria 1, 3, 4, 5 and the merge half of 2; no computed continuity; C1 breaks at most 2%; burden practical; genuine state gain | **Not met:** criteria 4 and 5 fail, no genuine gain. Criterion 1 on the first conversation is not explained by the control, which still fails it (activity F1 0.68 passes, adjusted Rand 0.64 and mention F1 0.57 fail) |
| **C. Stop** | evidence under 98%; C1 breaks over 5%; adjusted Rand under 0.50; C1 recovers under 60% of links | **None triggered:** 100%, 0.4%, 0.84 and 0.87, 66% |
| **B. Experimental tool** | otherwise | **This is the outcome** |

**B means:** keep the specification, scorer and these results as an offline analysis method. No schema, pipeline, ranking change or stored final state. No further activity experiments are recommended.

## What remains unknown
- **Whether an index would improve any answer.** Nothing tested this.
- **How a person would read these conversations.** Every reader and judge is Claude, using a scheme I wrote.
- **Whether two conversations from one dataset are typical.** They differ enough to change the results, so others could too.
- **The right granularity.** There may be none: 22 and 47 may both be defensible.
- **What "still continues" should mean.** Two judges under one rule split on 56 of 132 cases. That is a definition problem, and I don't believe a better prompt would settle it.

## Integrity
Readers received no ledgers, scores, conclusions or questions. Nothing was tuned, and the manual, specification, scorer, thresholds and classifier are hash-checked unchanged. There is no held-out data, schema change, retrieval change, paid call or merge. Conversation text, ledgers, cases, keys and judgements are outside this repository. The control's 3 invalid mentions of 171 (98.2%) stay as produced. The prefix rule was fixed but never needed.
