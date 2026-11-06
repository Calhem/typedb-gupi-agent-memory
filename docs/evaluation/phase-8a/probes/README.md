# Phase 8A probes
Read-only feasibility measurements, kept so the numbers in this folder can be reproduced. **These are not production
code and not evaluation results:** they ran on development splits and synthetic data, and several variants were tried.

| File | Measures | Needs |
|---|---|---|
| `feasibility_locomo_edges.py` | entity, neighbour and text-only expansion, reachability | `.data/`; no database |
| `feasibility_structure.py` | speaker and neighbour variants; LongMemEval development | `.data/`; no database |
| `traversal_latency.py` | path query latency on a synthetic graph with a hub | TypeDB; a disposable `gupi-probe-*` database |
| `validate_queries.py` | every query in `02-retrieval-design.md`, plus the Alice temporal answers | TypeDB; a disposable `gupi-probe-*` database |
| `results.txt`, `results-queries.txt` | their output: aggregates only, no dataset text | – |

Run from the repository root, for example `uv run python -I docs/evaluation/phase-8a/probes/feasibility_structure.py`
(`validate_queries.py` and `traversal_latency.py` without `-I`).
