# Phase 4 performance measurements

Date: 2026-11-03. One run on one machine (Apple Silicon laptop; TypeDB CE 3.14.1 in Docker, 10 CPUs and
about 7.7 GB visible to the container; Python 3.13 on the host). Indicative only, not a benchmark suite.
Raw numbers: `phase-4-performance.json`. Reproduce:
`uv run python -I scripts/benchmark_performance.py --people 100 200 500 2000 > docs/evaluation/phase-4-performance.json`

Data: a deterministic synthetic memory, three claims per person (one employment, two reporting lines; 30%
with stated ends), 80% accepted, 10% rejected, 10% left as hypotheses. Times are medians of 3 runs (the
Phase 3 comparison: 1 run).

| Claims | Ingest (claims/s) | ask ×20 | query (open role) ×10 | review queue (limit 20) | review queue, Phase 3 way | conflicts() | conflicts, Phase 3 way | keyword search | explore depth 2 |
|---|---|---|---|---|---|---|---|---|---|
| 300 | 142 | 0.086 s | 0.054 s | 0.065 s | 0.853 s | 0.129 s | 0.087 s | 0.024 s | 0.016 s |
| 600 | 151 | 0.085 s | 0.052 s | 0.076 s | 6.068 s | 0.277 s | 0.224 s | 0.040 s | 0.018 s |
| 1,500 | 158 | 0.084 s | 0.053 s | 0.085 s | not run | 0.618 s | not run | 0.090 s | 0.019 s |
| 6,000 | 157 | 0.086 s | 0.054 s | 0.197 s | not run | 2.604 s | not run | 0.426 s | 0.018 s |

Where both ran, the new and the Phase 3 code returned identical conflicts and queues.

## Reading
- **Flat with memory size:** `ask`, open-role `query` and `explore`. TypeDB selects the claims for one
  proposition, player or hop, so cost depends on the question, not on the memory.
- **Review queue:** 13× faster at 300 claims and 80× at 600 than the Phase 3 way, whose cost grew with the
  cube of the memory size (each hypothesis was compared with every pair of believed claims). At 6,000
  claims the Phase 3 queue did not finish within 30 minutes, so it is only timed up to 600.
- **Conflicts across the whole memory** grow roughly linearly (bucket queries plus comparisons inside
  buckets). At small sizes the Phase 3 way is slightly faster (fixed query overhead); its pairwise growth
  (2.6× for 2× the claims here) overtakes that as memory grows.
- **Keyword search** grows linearly: TypeDB 3.14.1 has no full-text index, so `contains` scans the text.
- **Ingestion** runs at about 150 claims per second (several small queries per record).
