# Phase 8G protocol: activity replication and decision

**Fixed before any reader ran:** this file, [the judging instructions](state-judging.md), `benchmarks/phase8g.json` and `phase8g_replication.py`. The 8F [manual](../phase-8f/annotation-manual.md), [specification](../phase-8f/consolidation-spec.md), scorer, thresholds and classifier are reused unchanged, pinned by hash and checked by a test.

**The conversation:** `conv-26`, the second development conversation. It holds no held-out questions.

## Who produces what
**No human annotator is involved. Every ledger and judgement comes from a Claude model, under one subscription.**
| Output | Producer | Instructions | Prior exposure |
|---|---|---|---|
| A | fresh Claude Opus 5.5 agent | manual | none |
| B | fresh Claude Sonnet 5.5 agent | manual | none |
| C1 | fresh Claude Sonnet 5.5 agent | specification | none |
| C2 | fresh Claude Haiku 5.5 agent | specification | none |
| A-control | fresh Claude Opus 5.5 agent, on the **first** conversation | manual | none |
| Judges 1 and 2, each conversation | fresh Claude Opus 5.5 and Sonnet 5.5 agents | judging instructions | none |

**One condition cannot be repeated.** In 8F, reader A was the session that built GUPI. That session has now seen the 8F conclusions, so using it would break the rule that readers get no conclusions. A is a fresh Opus agent instead, the nearest honest match. It also changes the comparison between the conversations, so A-control repeats that condition on the first conversation: 8F's A with B stays as reported, and A-control with B shows what the change itself does. A-control changes no 8F result.

**Isolation.** Each agent gets its own folder with only its instructions and conversation (and, for a judge, anonymous cases), uses only Read and Write, and is told to open nothing else. Agents automatically receive my memory index, so the line on this project is neutralised first and restored after. Tool calls are audited from transcripts. Any access outside its folder invalidates that run.

## Measures
All 8F measures, by the unchanged scorer. False separations are the agreed links an automated ledger fails to recover; false merges are agreed separations it breaks. Neither is called accuracy.

**One frozen criterion needs restating.** Criterion 4 asks that "the known kind of conflict" is reported by each ledger. Conflict was known in 8F because 8E had found it. Nothing is known here, and looking first would break the blind. So on this conversation it reads: A and B share at least one contradiction by turn overlap, and each automated ledger shares one with A or B. Numbers, thresholds and every other criterion are unchanged. `verdict` must reproduce the 8F verdict from the 8F numbers, which a test checks.

## Temporal states: correct, or merely alike?
Two ledgers given to one deterministic classifier can agree because the classifier collapses evidence, not because either is right. In 8F, asked a day after the end, it could only say unknown, ended or contradictory, so agreement may be partly built in. To separate these:

1. **Reference.** Every activity from every ledger becomes an anonymous case: person and quotes, in random order, with no label, role, state or source. Two blind judges decide its state from the whole conversation, by the manual's own rule, or say it is not one activity. **The reference is only what both judges agree on.** Everything else is undecided and left out. The judges are Claude, so this is a stated reference, not gold.
2. **Written against computed.** Each ledger's written state and its computed state are scored against the reference: correct, `unsafe` (claims engaged or ended where the reference says unknown), `wrong_way` (engaged against ended), and `missed` (says unknown where the reference is engaged or ended). Computed is `presumed` read as unknown, because the manual's engaged needs direct evidence. It is asked as 8F asked, a day after the end, and, separately, at the end itself.
3. **Decomposing agreement.** Each aligned pair is `both_agree`, `gained` (written differ, computed agree), `lost` or `neither`. A gain is split into: correct on shared evidence (**genuine**), correct on different evidence, correct by default (two unknowns with nothing deciding either), incorrect, or undecided. The last four are not genuine improvements.

**The agreement gain replicates** if the median computed kappa across the six pairs exceeds the median written kappa on both conversations. **It is a genuine gain in correctness** only if, for C1 on both conversations, computed scores at least 5 points above written on the reference, with no more unsafe plus wrong-way errors.

## Review burden and integrity
**Burden:** everything a reviewer must look at when nothing is auto-accepted: activities, `not_same`, contradictions and review items, per 100 turns. **Practical means at most 15 per 100 turns**, about one decision per seven turns. This is my judgement, set knowing 8F's C1 was near 10.

**Unsupported memories:** invalid evidence, activities the judges agree are not one activity, and unsafe written states.

## Decision rule
Set before seeing results. One outcome only, and "inconclusive" is not one of them.

**A. Implement a minimal review-first index**, only if, on conv-26: frozen criteria 1, 3, 4 and 5 and the merge half of criterion 2 all pass; invented continuity is 0 in computed states (the index never uses written states; written continuity is still reported); C1 breaks at most 2% of agreed separations; burden is practical; and computed states are a genuine gain. Failures of criterion 1 on the first conversation count against this and must be explained by A-control.

**C. Stop**, if any of: evidence falls below the frozen 98%; C1 breaks more than 5% of agreed separations; adjusted Rand between C1 and either reader is below 0.50 on conv-26, so the structure doesn't reproduce; or C1 recovers under 60% of agreed links.

**B. Keep as an experimental tool**, otherwise: it captures useful structure, but is too ambiguous for production.

## Limits fixed now
Two conversations from one dataset, both used in development. Claude's readers share a scheme I wrote, and share a vendor. Nothing here measures whether an index improves answers, or how a person would read these conversations.
