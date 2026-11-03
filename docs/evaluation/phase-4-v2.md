# Phase 4 benchmark under answer semantics v2

Date: 2026-11-03 (updated after the Q9 decision).

**Setup.** The benchmark is the original frozen Phase 4 one, unchanged:
- **Data:** the questions, gold answers and world in `tests/fixtures/retrieval`, frozen in `be7c01a`.
- **Scoring:** `gupi.retrieval_eval.score`.

Only the structured system's answer semantics differs. Reproduce with:

    uv run python -I -m gupi.retrieval_eval --semantics v1
    uv run python -I -m gupi.retrieval_eval --semantics v2 --json docs/evaluation/retrieval-v2.json

**Results:**
- The v1 rerun reproduces the committed `retrieval-v1.json` exactly, apart from timings.
- v2's raw results are in `retrieval-v2.json`.
- The keyword baseline does not use answer semantics, and is unchanged at 5/15.

## Side by side (structured system)
| Configuration | Semantics | Answers correct | Abstained when it should (of 6) | Unsupported assertions | Citation precision / recall | Median time per question |
|---|---|---|---|---|---|---|
| gold claims | v1 | 15/15 | 6 | 0 | 0.963 / 1.000 | about 0.02 s |
| gold claims | **v2** | **13/15** | 6 | 0 | 0.833 / 0.833 | about 0.02 s |
| rule-extracted | v1 | 15/15 | 6 | 0 | 0.963 / 1.000 | about 0.02 s |
| rule-extracted | **v2** | **13/15** | 6 | 0 | 0.833 / 0.833 | about 0.02 s |

These are not combined with the v2 acceptance results (tests/acceptance: 26 of 26 v2 rows pass), and no
single "improvement" figure is given.

**Remember that the gold answers were written under v1.**
- **What the gold assumes:** two of the 15 gold answers rely on v1 rules that v2 deliberately replaces. One
  treats a later start as evidence of falsity; the other treats a joined period as directly true.
- **What the frozen scoring does:** it counts any answer other than the gold one as wrong, including
  PRESUMED and a more cautious UNKNOWN.
- **What we did not do:** change the gold or the scoring.

## Every changed answer
Both configurations change in the same way.

| Question | Gold (v1-era) | v1 | v2 | Why it changed | Assessment |
|---|---|---|---|---|---|
| q01 "Did Nora Vance work at Halden in mid-March 2025?" | TRUE | TRUE (joined from w1-1 and w1-3) | **UNKNOWN**, window: w1-1, w3-3 | Two start statements disagree (Q9, judged claim by claim; see below). w1-1 supports; w3-3 is too imprecise to decide. | **More cautious, for a stated reason.** Not forced to TRUE. |
| q03 "Did Leah Ortiz work at Halden in mid-May 2025?" | FALSE | FALSE (from w1-5's start) | **UNKNOWN**, no coverage | The only evidence is w1-5, "joined Halden as CTO in June 2025". v1 read a start as FALSE for all earlier time. Q1, approved, says a start is not negative evidence. | **More cautious, and intended** (decision Q1; row R15). The gold FALSE rests on the rule v2 removes. |

### q01 in detail (Q9 decided claim by claim)
The queried instant is **15 March 2025** (`valid_at` 2025-03-15), as believed on 1 October 2025.

| Claim | Source wording | Recorded | As a start | At 15 March |
|---|---|---|---|---|
| w1-1 | "Nora Vance joined Halden as CTO in January 2025." | 15 Jan 2025 | in [1 Jan, 1 Feb 2025) | **supports**: certainly started by 15 March, and the period continues to the recorded departure in May (w1-3), with no termination between |
| w3-3 | "Since March 2025, Nora Vance works at Halden as CTO." | 20 Aug 2025 | in [1 Mar, 1 Apr 2025); still true on 20 Aug | **imprecise**: "since March" may mean a date after 15 March |
| w1-3 | "Nora Vance left Halden in May 2025." | 2 Jun 2025 | (an end, in May) | not a start; the end of w1-1's period |

**Result:** UNKNOWN (basis: window; claims w1-1 and w3-3). The explanation reads: "the start date is
disputed. w1-1 places the start before 2025-03-15, but the date given by w3-3 is too imprecise to say
whether it was before or after 2025-03-15. The true start is not assumed to lie between them." Neither
statement is preferred.

**Justification:**
- If w3-3's start is right, Nora may have joined after 15 March.
- Nothing in the documents narrows "since March".
- So the documents do not establish her employment on that date. UNKNOWN is the answer the Q9 rule
  requires.
- The frozen gold, TRUE, was written under v1. It is kept, so q01 still counts as a miss.

**Ambiguity that remains:**
- **Reading of "since March 2025".** It is encoded, both in the benchmark's gold claim and by the rule
  extractor, as a start window in March. A reader could take it as "at least since March", without dating
  the start.
- **Under that reading, w3-3 would not compete with w1-1,** and q01 would be PRESUMED (joined from w1-1 to
  w1-3). That is still not TRUE under the frozen scoring.
- **Where the choice belongs:** this is a question of how the sentence is turned into a claim (extraction, or
  the gold annotation), not of the v2 semantics. It is left as found.

Unchanged answers whose **citations** changed:
- **q05** ("Who was Halden's CTO in mid-July 2025?", CONTESTED): v1 also cited w1-5, an undecided candidate,
  which the Phase 4 report noted as remaining imprecision. v2 cites exactly the gold evidence, w1-3 and
  w3-3. This is a **correction**.
- **q06 and q15** (UNKNOWN): v1 cited w1-2 ("Ivo Marsh reports to Nora Vance", true on 15 January) for an
  instant it does not cover. v2 cites nothing, because no evidence decides the instant. These questions have
  no gold evidence, so this does not change the citation scores.

**Why the citation scores fell:**
- They fall only because of q01 and q03.
- q01 under v2 cites the two start statements behind the window, against gold w1-1 and w1-3: precision and
  recall 0.5.
- q03 cites nothing, against gold w1-5: 0 and 0.

**No regressions.**
- No question went from correct to a confident wrong answer.
- No unsupported assertion was added.
- Abstention stayed 6/6.

## Performance
- **Per question:** the median time is unchanged (about 0.02 s, varying by a few milliseconds between runs). It is dominated by the TypeDB queries, which are
  the same under both semantics.
- **The classifier alone:** about 5 µs per call against v1's 2 µs, averaged over the 26 truth-table cases
  on this laptop.
- **How it scales:** the joined-period search grows with (starts × targets × ends) for one proposition,
  which is fine for the handful of claims a proposition has. It would need indexing only for propositions
  with hundreds of boundary statements.
