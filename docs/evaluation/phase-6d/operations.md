# Phase 6D operational performance (first run)

**Setup:**
- **Machine:** Apple M2 Pro (10 cores, 16 GB). TypeDB 3.14.1 runs in Docker Desktop (10 CPUs, 7.7 GB),
  with Python on the host.
- **Runs:** one run each. Timings are indicative, and the store probe uses synthetic load (see PLAN.md).
- **Sources:** the figures come from `first-run/*.json` (`timings`, `latency`, `database`, `steps`).
- **Database size:** the size of the database's directory in the TypeDB container (`du`).
- **Empty databases:** an empty GUPI database with its schema is about 21.4 MB.

## Ingestion (write side)
| Step | LoCoMo held-out | LongMemEval subset | LongMemEval held-out | D1 world |
|---|---|---|---|---|
| turns | 5,094 | 31,839 | 220,178 (extraction only, no TypeDB) | 11 |
| turn ingestion | 26.9 s (189/s) | 185.5 s (172/s) | — | 0.09 s |
| rules:v2 extraction | 0.19 s (26,600/s) | 4.0 s (7,900/s) | 30.7 s (7,180/s) | 0.007 s |
| candidates / store submissions | 0 / 0 s | 0 / 0 s | 0 | 11 / 0.38 s (35 ms each) |
| embeddings | 96.2 s (53/s, short turns) | not run (Phase 5: 3,536 s, 9/s) | — | 0.05 s |
| database size | 24.7 MB, 59.1 MB with embeddings | 139.6 MB (Phase 5 with embeddings: 359 MB) | — | 21.4 MB |
| peak Python memory | 0.61 GB | 2.1 GB (parsing the 277 MB JSON) | 2.1 GB | — |

**What the costs are made of:**
- **Formation's own cost on these datasets is zero,** because nothing was extracted. Ingestion cost is the
  turns, plus embeddings where computed.
- **Embedding is the dominant cost** wherever it runs, as in Phase 5.

## Candidate store as it grows (synthetic: renamed copies of the 32 D3 passages)
| Observations | Candidates | Claims | Pending | `pending()` | Submit per observation | v2 query p50 / p95 | Database |
|---|---|---|---|---|---|---|---|
| 128 | 120 | 80 | 24 | 0.023 s | 26.6 ms | 16 / 36 ms | 22.0 MB |
| 384 | 360 | 240 | 72 | 0.064 s | 23.9 ms | 17 / 35 ms | 23.2 MB |
| 640 | 600 | 400 | 120 | 0.109 s | 22.7 ms | 15 / 42 ms | 24.5 MB |
| 992 | 930 | 620 | 186 | 0.193 s | 22.8 ms | 15 / 34 ms | 26.3 MB |

**What the probe shows:**
- **Submission time and query latency are flat:**
  - **Submission:** about 23 ms per observation with candidates. It is dominated by its TypeDB reads and one
    write transaction per candidate.
  - **Queries:** v2 answers read only the proposition's claims.
- **`pending()` grows linearly with the store,** at about 0.2 ms per stored candidate. This confirms known
  issue S4: it reads every candidate. At 100,000 candidates it would take about 20 s.
- **Storage:** about 5 KB per observation with its candidates, decisions, claims and reviews.
- **Per observation, alongside submission:** ingestion took 8.9 ms and extraction 0.26 ms.
- **Incremental behaviour:**
  - **Resubmitting:** the last 32 observations took 0.44 s and wrote nothing (930 decisions, 930 candidates
    and 620 claims before and after).
  - **Adding a copy:** each new copy cost the same as the first, with no slowdown from the existing data,
    apart from `pending()`.

## Query (read side)
| System | Where | p50 | p95 |
|---|---|---|---|
| GUPI v2 answer (with qualification) | D1 | 0.026 s | 0.060 s |
| GUPI v2 answer | D4 | 0.019 s | 0.035 s |
| keyword answer heuristic | D1 | 0.004 s | 0.005 s |
| keyword retrieval | LoCoMo | 0.043 s | 0.069 s |
| embedding retrieval | LoCoMo | 0.071 s | 0.094 s |
| hybrid-unfiltered | LoCoMo | 0.114 s | 0.154 s |
| hybrid (structure-filtered) | LoCoMo | 0.186 s | 0.241 s |
| structured | LoCoMo | 0.074 s | 0.105 s |
| keyword retrieval | LongMemEval subset | 0.110 s | 0.273 s |

**Notes on these latencies:**
- **What they include:** retrieval latencies cover reading the scope from TypeDB, and for embeddings, the
  vectors too (exact cosine in NumPy; there are no native vectors).
- **Total retrieval time:** LoCoMo took 855 s for 1,676 questions × 5 systems.

## Not measured
- **TypeDB server CPU and memory over time:** one sample during the LoCoMo run showed 377 MB. A proper
  measurement needs container monitoring that was not set up.
- **Disk I/O.**
- **Concurrent clients.**
