# Phase 4 report: structured retrieval

Date: 2026-11-03. Branch: `feature/phase-4-retrieval` (from `main` at `0a860eb`, where Phases 2 and 3 were
merged after verification). Server: TypeDB CE 3.14.1; typedb-driver 3.14.0; Python 3.13. Entirely
offline: no credentials, paid services, embeddings or LLM question answering.

## Merge of Phases 2 and 3
Branch history reviewed (9 + 7 commits, linear stack, no possible conflicts); 141 tests passed on the stacked
branch; extraction benchmarks byte-for-byte unchanged; no secrets or unintended files. One test-only tidy
(a reviewer name in CLI tests made neutral, `a7ae4c7`). Merged in order with `--no-ff`; tests passed after
each merge (120, then 141); remote `main` verified at `0a860eb`.

## Owner requirements
| Requirement | Delivered | Tested in |
|---|---|---|
| Structured retrieval, citations, temporal context, explicit unknowns | `Memory.query` / `query_by_name` | test_query.py |
| Filtering in TypeDB; no load-all, no unrestricted pairwise comparison | per-claim TypeQL functions (core/0007-0008), candidate queries, bucketed conflicts; a test fails if a retrieval path loads all claims | test_server_filtering.py, test_query.py, test_explore.py |
| Multi-hop exploration and historical views | `explore`, `follow`, `history` | test_explore.py |
| Keyword search baseline | `Memory.search` (TypeDB `contains` + BM25) | test_search.py |
| Benchmark vs keyword-only on a frozen dataset | `gupi.retrieval_eval`; dataset frozen before the query code | test_retrieval_eval.py; docs/evaluation/phase-4-retrieval.md |
| Conflicting, rejected and hypothetical claims handled | CONTESTED answers; rejected / unreviewed / superseded / later-recorded claims excluded with reasons | test_query.py, benchmark q02 q05 q07 q08 q11 |
| Conflict rules configurable; identity suggestions provisional | `Memory(constraints=...)` or pack `constraints.json`; identities still merge only when accepted | test_server_filtering.py, test_identity.py |

## Correctness issues found and fixed
1. A start in one statement and an end in another ("joined in January", "left in May") gave UNKNOWN for
   March. Now assembled into TRUE, labelled as assuming one continuous period (found while writing the
   frozen questions, before the code).
2. The same-spell rule treated "since June" and "stopped in July" as possibly different spells; a window's
   latest bound is now exclusive.
3. Value questions ("was she CTO?") ignored a departure statement that gave no title; such claims can now
   say FALSE (never TRUE).
4. As-of name resolution leaked later knowledge (found by the benchmark's first run; fixed separately).

## Results
- **Tests:** `uv run pytest -q` **160 passed**, none skipped, against the live server. New in Phase 4: spells
  and assembly (4), server-side filtering (4), query (5), explore/history (3), search (2), benchmark runner (1).
- **Retrieval benchmark (first run):** structured 13/15 with 0 unsupported assertions; keyword-only 5/15 with 4.
  After the as-of fix: structured 15/15 (not an unbiased estimate). Details: docs/evaluation/phase-4-retrieval.md.
- **Performance** (docs/evaluation/phase-4-performance.md): `ask`, open-role `query` and `explore` stay flat
  from 300 to 6,000 claims (about 4 ms, 5 ms and 18 ms each); the review queue is 13-80× faster than the
  Phase 3 way at 300-600 claims (that approach did not finish in 30 minutes at 6,000); whole-memory conflict
  detection grows about linearly (2.6 s at 6,000); keyword search grows linearly (0.43 s at 6,000);
  ingestion runs at about 150 claims per second.
- **Extraction benchmarks:** unchanged (fingerprints match; re-runs identical).

## Decisions
ADR 0007 (new): filtering in TypeDB, spell assembly, value questions, the query result, as-of name
resolution, the keyword baseline and the benchmark protocol.

## Limitations
- Questions are structured; there is no natural-language question interface (deferred with LLM answering).
- Keyword search scans text (no full-text index in TypeDB 3.14.1) and has no stemming; no embeddings.
- Whole-memory conflict detection is linear but slow at scale (2.6 s at 6,000 claims); it is a batch tool,
  not for every request. Small memories are slightly slower than before because of query overhead.
- Spell assembly assumes one continuous period between a stated start and a stated end.
- Ingestion throughput (about 150 claims per second) will limit Phase 5 datasets.
- Open-role questions cite undecided candidates when the overall answer is CONTESTED.
- The benchmark is small and synthetic; its world uses phrasings the rule extractor already handles.
- The freeze commit's message miscounts the answer mix ("TRUE 5"); the files and README are correct
  (TRUE 4, FALSE 3, UNKNOWN 4, NOT_YET_KNOWN 2, CONTESTED 2).

## Commits
`be7c01a` frozen benchmark + plan · `47270d6` filtering in TypeDB, spell assembly · `cb2084f` query ·
`3df62a6` explore/history · `e6682e1` keyword search · `b5b48be` benchmark runner + first run ·
`d59a7ec` as-of name fix · plus this commit (performance script and results, ADR 0007, report, Phase 5 plan).

## Next
Phase 5 proposal: docs/phase-5-plan.md (LoCoMo and LongMemEval; what can be done offline, and the
decisions on licences, downloads, LLM budget and embeddings).
