# Phase 4 benchmark under answer semantics v2

Date: 2026-11-03.

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
| gold claims | v1 | 15/15 | 6 | 0 | 0.963 / 1.000 | 0.018 s |
| gold claims | **v2** | **13/15** | 6 | 0 | 0.833 / 0.833 | 0.018 s |
| rule-extracted | v1 | 15/15 | 6 | 0 | 0.963 / 1.000 | 0.018 s |
| rule-extracted | **v2** | **13/15** | 6 | 0 | 0.833 / 0.833 | 0.018 s |

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
| q01 "Did Nora Vance work at Halden in mid-March 2025?" | TRUE | TRUE (joined from w1-1 and w1-3) | **UNKNOWN**, window: w1-1, w3-3 | w1-1 says she joined in **January**; w3-3, written in August, says "**since March**", and that she is still CTO. These are two start statements with disjoint windows and no end between them. Under the provisional **Q9** rule, the start then lies anywhere from January to March, so mid-March is inside an uncertain window. | **More cautious, and caused by an open decision (Q9).** The spec's earlier prediction was PRESUMED, from w1-1 to w1-3. That is what option (c) of Q9 would give. Neither PRESUMED nor UNKNOWN matches the v1-era gold TRUE. |
| q03 "Did Leah Ortiz work at Halden in mid-May 2025?" | FALSE | FALSE (from w1-5's start) | **UNKNOWN**, no coverage | The only evidence is w1-5, "joined Halden as CTO in June 2025". v1 read a start as FALSE for all earlier time. Q1, approved, says a start is not negative evidence. | **More cautious, and intended** (decision Q1; row R15). The gold FALSE rests on the rule v2 removes. |

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
- **Per question:** the median time is unchanged (0.018 s). It is dominated by the TypeDB queries, which are
  the same under both semantics.
- **The classifier alone:** about 5 µs per call against v1's 2 µs, averaged over the 26 truth-table cases
  on this laptop.
- **How it scales:** the joined-period search grows with (starts × targets × ends) for one proposition,
  which is fine for the handful of claims a proposition has. It would need indexing only for propositions
  with hundreds of boundary statements.
