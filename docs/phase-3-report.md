# Phase 3 report: reconciliation, review and identity

Date: 2026-11-02. Branch: `feature/phase-3-reconciliation` (stacked on `feature/phase-2-extraction`, which
is not merged yet). Server: TypeDB CE 3.14.1; typedb-driver 3.14.0; Python 3.13.

## Gate
"Correction, retraction, contradictory sources, retroactive updates and identity merge/split;
observation kept distinct from accepted knowledge; history preserved; tests for as-of valid time and
as-of recorded time, including conflicting sources and uncertain dates." **Met**, with the tests below.

## Priorities
| # | Priority | Delivered | Tested in |
|---|---|---|---|
| 1 | Review queue, historical decisions | queue at any time t, batch decisions in one transaction, history timeline | test_review.py |
| 2 | Contradiction vs differing evidence | four classes; domain constraints; same-spell rule for FALSE | test_conflict_rules.py, test_conflicts.py |
| 3 | Suggested identity, no auto-merge | identity hypotheses with reasons; merge only once accepted; split on retraction | test_identity.py |
| 4 | Reversible corrections, out-of-order | reviewable supersessions; suggestions by observed-at; late and early arrivals | test_corrections.py |
| 5 | Minimal CLI | `gupi` queue/show/accept/reject/retract/conflicts/identities/corrections/supersede/unsupersede/ingest | test_cli.py |

## Found and fixed along the way
- `ask()` called separate spells (2020-2021, then 2024-) CONTESTED, and an earlier spell plus a present claim
  with an unstated start FALSE. Both now follow the same-spell rule (ADR 0006); all earlier temporal tests
  still pass unchanged.
- Correction suggestions initially proposed replacing an older job title with a newer one; that would erase
  a possible promotion, so values that may be sequential are no longer suggested.

## Tests
`uv run pytest -q`: **141 passed**, none skipped, against the live server. New in Phase 3: review (3), conflict
rules (6), conflicts (3), identity (2), corrections and order (4), CLI (3); migration tests made independent
of the number of migrations.

## Extraction benchmarks
Unchanged: fixture, rule-extractor and saved-result files have the same SHA-256 as at the start of Phase 3,
and re-running both evaluations reproduces the saved results byte for byte (held-out re-run only for this
check). These are results of the **offline rule extractor** and say nothing about LLM extraction; the Claude
evaluation remains deferred until credentials exist ($0 spent).

## Decisions
ADR 0006 (new). ADRs 0001-0005 unchanged except that ADR 0003's open question on reversible supersessions
is answered by ADR 0006.

## Limitations
- Identity suggestions are name-based only (no attributes, no context beyond the conversation); a
  common first name in one conversation can produce wrong suggestions, which is why nothing merges unaided.
- Conflict detection is pairwise over all believed claims (quadratic); fine for tests, not for large memories.
- Nothing prevents accepting two alternative readings, or two contradictory claims; they are reported, not blocked.
- The queue and conflicts read every claim into Python; no server-side filtering yet.
- The CLI has no pagination, colour or interactive mode; claim ids are shown as 10-character prefixes.
- Supersessions are suggested only within one source; cross-source corrections are left to reviewers.
- Phase 2 limitations still apply (rule-extractor recall, no live Claude run, single-process ledger).

## Commits
`53d04b4` plan · `9927c6e` review queue · `04726e6` conflicts · `cc68eee` identity · `e6c7921` corrections
· `f3f1475` CLI · plus this documentation commit.

## Next
Phase 4 proposal: docs/phase-4-plan.md.
