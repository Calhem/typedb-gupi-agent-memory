# Phase 8B.1: conversational relationship retrieval

**Development data only. Not a benchmark or leaderboard result.** Reproduce with
`uv run python -I -m gupi.benchmarks.phase8 --dataset locomo` (or `longmemeval`). The runner has no held-out option.
Configuration: `benchmarks/phase8b.json`. Raw results: `results/8b1-*.json`.

## What was built
`gupi/paths.py`: `conversational()`, plus `Memory.retrieve()`. Keyword hits stay; the top 3 keep their places; each hit
brings the turn on either side; hits by the one speaker a question names move up, and nothing is ever removed. The
ranking functions are pure and tested without a database. No schema change, model call or new dependency.

**TypeDB queries added** (`gupi/paths.py`): `MEMBERS` (a context's turns with `observed-at`, `received-at`) and
`AUTHORS` (`authorship` with the author's label).

**Belief time:** `conversational` honours `believed_at` through `received-at`, closing the gap `evidence.keyword` has.

## Did the baseline reproduce?
**Yes, exactly.** Keyword matches Phase 5 on all 301 LoCoMo questions, per question, at R@5 and R@10. LoCoMo still has
0 claims.

## Did the Phase 8A gain survive?
**Yes.** Implementation scored slightly above the probe on most lines (the probe's overall R@10 was 0.693).

**LoCoMo development, turn recall, `keyword → conversational`:**
| Category | R@5 | R@10 | R@50 | Added@10 | Displaced@10 |
|---|---|---|---|---|---|
| multi-hop (42) | 0.132 → 0.187 | 0.195 → **0.313** | 0.383 → 0.455 | 0.29 | 0.02 |
| single-hop (114) | 0.500 → 0.548 | 0.548 → 0.737 | 0.702 → 0.855 | 0.19 | 0.00 |
| temporal (63) | 0.762 → 0.794 | 0.825 → 0.857 | 0.936 → 0.952 | 0.03 | 0.00 |
| adversarial (71) | 0.599 → **0.570** | 0.711 → 0.789 | 0.810 → 0.915 | 0.17 | 0.08 |
| open-domain (11) | 0.136 → 0.182 | 0.318 → **0.273** | 0.364 → 0.485 | 0.00 | 0.09 |
| **all (301)** | **0.513 → 0.541** | **0.587 → 0.698** | **0.720 → 0.820** | | |

Added and displaced are gold items per question, relative to keyword's top k.

**Precision@10:** 0.050 → 0.076 on multi-hop; 0.073 → 0.082 on adversarial.

**LongMemEval development, keyword → conversational (turn):**
| | R@5 | R@10 | R@50 |
|---|---|---|---|
| all (49) | 0.775 → **0.745** | 0.867 → **0.857** | 0.958 → **0.927** |
| multi-session (8) | 0.479 → 0.417 | 0.542 → 0.542 | 0.740 → 0.677 |
| temporal-reasoning (13) | 0.782 → 0.744 | 0.859 → 0.821 | 1.000 → 0.923 |

Session level: R@5 and R@10 unchanged (0.923, 0.958); R@50 0.976 → 0.962.

## Reading the results
- **Question A is answered, for LoCoMo only.** Conversational structure helps there, and adversarial R@5 falls 2.9 points.
- **It does not generalise yet.** LongMemEval got slightly worse. Sessions are long and questions paraphrase: neighbours
  displace real hits. No fix was tuned here; **a setting that helps one dataset and harms another should be chosen
  per-dataset only with a reason.** The same pool of 50 is a hard cut, so neighbours push later hits out, which is what
  lowers R@50. With AML's depth of 100 this effect should be smaller (*hypothesis*).
- **Latency:** LoCoMo p50 0.059 s (keyword 0.019 s), p95 0.101 s. LongMemEval p50 0.19 s (keyword 0.11 s), p95 0.41 s.
- **This is still not a TypeDB advantage.** Authorship and turn order would work in any store.
