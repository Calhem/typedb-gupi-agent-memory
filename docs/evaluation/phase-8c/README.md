# Phase 8C: real-conversation memory evaluation

**Status: stopped at the first paid-call gate. No paid call has been made.** Nothing here is a benchmark or leaderboard
result. The central question, whether structured knowledge improves real memory performance, is **not yet answered**:
everything needed to answer it is built, and it needs the owner's approval to spend.

| Stage | State | Document |
|---|---|---|
| 8C.1 extraction adapter | built, offline tested | [run-plan.md](run-plan.md) |
| 8C.2 cross-session identity | built, tested | [identity-design.md](identity-design.md) |
| 8C.3 independent evaluation | external set frozen; independent pack needs an author | [scoring.md](scoring.md), [authoring brief](independent-authoring-brief.md) |
| 8C.4 answer harness | built, offline tested; no paid call | below |

## Architecture
```
message ─► gpt-4o-mini (recorded first; replay needs no model) ─► model:candidate-v1.1 (unchanged)
        ─► candidate store and formation:v1 (unchanged) ─► claims, review items, withheld items
session links (hypotheses, with reasons) ─► paths.retrieve ─► evidence ─► answer ─► judge ─► where it broke
```
The parser, validator, formation policy, candidate store, temporal code and schema are unchanged. No new database,
framework, service or dependency. TypeDB remains the only persistent store. Recordings are files in git-ignored `.data/`,
as Stage 3's raw responses were, because they quote datasets.

## Extraction adapter compatibility
| Requirement | How it is met |
|---|---|
| `model:candidate-v1.1` and formation | replies go through the existing parser and `store.submit`, unchanged |
| Not `ClaudeExtractor` | not imported; a test checks |
| `gpt-4o-mini` | re-verified 2026-11-06 |
| Raw evidence | observations are stored first; every claim points to its span |
| Time, provenance, corrections, allegations | code reads them, as before; tests cover each through the store |
| Replay | one recording per request; a changed prompt or context misses it; replay rebuilds identical claim ids |
| Costs, failures, outcomes | `Tally` keeps replies, parser outcomes and decisions apart; spending goes through the ledger |

**The only change made to a model reply** is removing the nulls OpenAI's strict mode forces into optional fields.

## Answer-level harness (8C.4)
`src/gupi/benchmarks/phase8c_answers.py` answers with the prompts of AML's published LoCoMo-Refined pipeline at commit
`f4f82ffb`, then judges CORRECT or WRONG, and assigns each question one first cause:
extraction, formation or review, retrieval, ranking, answer generation, unsupported, temporally invalid, or unjudged.

- **AML's repository has no licence,** so its prompts are not copied here. The harness reads a hash-checked private copy
  in `.data/` as data, and never runs it.
- **AML's answer and judge models are not published.** `gpt-4o-mini` stands in, so these can never be AML scores.
- **Do qualifications help?** The same evidence is rendered with and without its notes, so the difference is due to the
  qualifications alone.
- **Disclosed tension:** AML's prompt says to prefer the most recent memory when memories conflict, which may override GUPI's
  refusal to resolve disputes.

## Evaluation criteria
| # | Question | Measured by | Needs |
|---|---|---|---|
| 1 | Is the graph connected enough? | `graph_report` | Gate 1 |
| 2 | Does traversal find what text misses? | C over B and D; `gold_turns_only_claims_found` | Gate 2 |
| 3 | Does it rank better on tight budgets? | R@5 and R@10 | Gate 2 |
| 4 | Do qualifications improve answers? | qualified against plain | Gate 3 |
| 5 | Is it worth the cost? | all of the above against [cost](run-plan.md) | Gates 2 and 3 |

## Known limitations
- **No extraction has run.** Every test uses scripted replies. Nothing here shows `gpt-4o-mini` can do this.
- The largest risks are in the [run plan](run-plan.md), and they are predictions.
- The external set has no provenance or identity questions, and the small sample means wide intervals.
- Depth-100 recall on one 600-turn conversation is an easier task than on a long history.
- `paths.py` is about 490 lines, above the 300-line guide.
- Per-message extraction does not scale to AML's corpus.
