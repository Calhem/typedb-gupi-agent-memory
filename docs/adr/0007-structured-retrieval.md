# ADR 0007: Structured retrieval, filtering in TypeDB, and the keyword baseline

Status: accepted (Phase 4), 2026-11-02

## Filtering happens in TypeDB
- Per-claim functions (core/0007): `believed_claim($c, $t)`, `hypothesis_claim($c, $t)` and
  `in_force_supersessions($c, $t)` take a claim, so TypeDB evaluates them only for candidates the rest of
  the query has found. `believed_at($t)` is redefined on top of `believed_claim` (core/0008): one
  definition of "believed". `gupi.status` keeps the same rules for explanations and history; tests check
  that the two agree.
- Candidates are found by proposition key, role player, type, values and recording time in TypeQL; only
  those claims are fetched (one query for many ids, via `given` rows).
- Conflicts are compared only inside buckets TypeDB finds: proposition keys with two or more believed
  claims, players shared under a one-at-a-time rule (`reduce count groupby`), and accepted identity groups.
  The review queue compares each hypothesis only with believed claims that could conflict with it.
  Identity suggestions group referents by exact label in TypeDB.
- `Memory.all_claims()` stays for tests and debugging; a test fails if any retrieval path calls it.

## Answering one proposition (`gupi.answering`)
- Per-claim verdicts and the same-spell rule as in ADR 0006, with one correction: a window's latest bound
  is exclusive, so "since June" and "stopped in July" are certainly one spell, while exact back-to-back
  bounds (ended 1 Jan, started 1 Jan) are two.
- **Spell assembly:** if believed claims certainly started by v and certainly had not ended by v (from
  different statements, e.g. "joined in January" and "left in May"), and none counts as FALSE at v, the
  answer is TRUE, with a note that it assumes one continuous period. Assembly never overrides a FALSE.
- **Value questions** ("was she CTO?"): claims about the same relationship without that value count only
  when they say FALSE (if the job had ended, so had the title).

## Questions (`gupi.query`)
- A `Question` has a claim type, fixed roles, at most one open role, optional values, a valid time and a
  belief time. The `Result` gives the overall answer and one per candidate, citations, exclusions with
  reasons, the temporal context and the retrieval steps.
- Citations are the evidence *for* the answer: TRUE verdicts for TRUE (plus both claims of an assembled
  spell), FALSE for FALSE, both for CONTESTED, the undecided ones for UNKNOWN.
- Excluded claims are listed with why: rejected or retracted (by whom, when, why), an unreviewed
  hypothesis, superseded, recorded after the belief time, a different value, a different period.
- Open roles: one TRUE candidate or several give TRUE with the names; any CONTESTED candidate gives
  CONTESTED; all FALSE gives FALSE; otherwise UNKNOWN, or NOT_YET_KNOWN when nothing was recorded.
- Names resolve to referents **known at the belief time** (mentioned in observations received by then);
  a name matching several referents not accepted as the same is reported as ambiguous, never guessed.

## Exploration and history (`gupi.explore`)
`explore` walks believed claims one TypeDB query per hop with depth and node limits; `follow` chains
structured questions and stops where an answer is not TRUE; `history` lists records and decisions in
transaction-time order with each claim's valid-time period.

## Keyword baseline (`gupi.search`)
TypeDB's `contains` (case-insensitive in 3.14.1) selects candidate observations received by the belief
time; Python keeps whole-word matches and ranks with BM25 (corpus size from a TypeDB count, average length
over candidates, no stemming). No embeddings: deferred by the owner.

## Benchmark protocol
The world and questions in `tests/fixtures/retrieval` were committed before the query code. The first
run is recorded unchanged (`docs/evaluation/retrieval-v1-first-run.json`). A bug it exposed (as-of name
resolution) was fixed in a separate commit and the run repeated; that second score is reported as
post-fix, not as an unbiased estimate. Tests check the runner works but do not pin scores.
