# Phase 4 retrieval benchmark: structured vs keyword-only

Data: `tests/fixtures/retrieval` (3 synthetic conversations, 11 messages, 15 questions), frozen in commit
`be7c01a` before any query code. Reproduce: `uv run python -I -m gupi.retrieval_eval`.
Offline; no LLM, no embeddings. Raw results: `retrieval-v1-first-run.json` (first run, unchanged) and
`retrieval-v1.json` (after the fix below).

| Configuration | System | Answers correct | Abstained when it should (of 6) | Unsupported assertions | Citation precision / recall |
|---|---|---|---|---|---|
| gold claims | structured, **first run** | 13/15 | 6 | 0 | 0.96 / 1.00 |
| gold claims | structured, after fix | 15/15 | 6 | 0 | 0.96 / 1.00 |
| gold claims | keyword only | 5/15 | 2 | 4 | 0.67 / 0.56 |
| rule-extracted | structured, **first run** | 13/15 | 6 | 0 | 0.96 / 1.00 |
| rule-extracted | structured, after fix | 15/15 | 6 | 0 | 0.96 / 1.00 |
| rule-extracted | keyword only | 5/15 | 2 | 4 | 0.67 / 0.56 |

"Unsupported assertions": answering TRUE, FALSE or CONTESTED where the gold answer is UNKNOWN or
NOT_YET_KNOWN. Median time per question: structured about 0.02 s, keyword about 0.004 s.

## How to read this
- **First run is the headline.** Its two misses (q11, q12, both "as known on ..." questions) exposed a bug:
  names were resolved with referents GUPI only learned about later. That was fixed in a separate commit and
  the run repeated; because the fix was prompted by these questions, 15/15 is not an unbiased estimate.
- **Keyword-only retrieval** finds relevant passages but cannot tell a rejected or unreviewed statement from
  an accepted one (q07, q08), has no valid time (q01, q03, q04, q06, q15), and cannot see a contradiction
  (q02, q05). This is the expected gap between text retrieval and bitemporal, reviewed claims, and the
  baseline is deliberately simple (rules in `gupi/retrieval_eval.py`).
- **Rule-extracted = gold here** because every message in this world uses phrasings the offline rule
  extractor handles (its development set is similar). This world does not test extraction; Phase 2's
  held-out extraction recall (0.50) still applies to unfamiliar wording. None of this is evidence about LLM
  extraction.
- Remaining citation imprecision: for an open question answered CONTESTED (q05) the result also cites an
  undecided candidate's claim. Left as measured.
- 15 questions is a behavioural check, not a statistical estimate.

## Under answer semantics v2 (added 2026-11-03)
The same frozen benchmark was rerun with the structured system under answer semantics v2 (docs/adr/0009).
The questions, gold answers and scoring are unchanged, and v1 remains the default.

| Configuration | v1 | v2 |
|---|---|---|
| gold claims | 15/15 | 13/15 |
| rule-extracted | 15/15 | 13/15 |

Both changed answers are more cautious, not confident errors:
- **q01** ("Did Nora Vance work at Halden in mid-March 2025?") becomes **UNKNOWN**.
  - w1-1 ("joined ... in January 2025") supports employment on 15 March.
  - w3-3 ("Since March 2025 ...") dates a competing start too imprecisely to say whether it was before or
    after 15 March (Q9).
  - The known issue about reading "since" as a start applies (docs/known-issues.md).
- **q03** ("Did Leah Ortiz work at Halden in mid-May 2025?") becomes **UNKNOWN**, because a start in June is
  not evidence of falsity in May (Q1).

Under v2, q05's citations match the gold exactly. Abstention is 6/6 and there are no unsupported
assertions. Details, every changed answer and raw results: phase-4-v2.md and retrieval-v2.json.
