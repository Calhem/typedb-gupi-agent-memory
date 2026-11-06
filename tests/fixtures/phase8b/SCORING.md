# Scoring rules for the claim-path fixture

Fixed before any claim-path code. Systems: A keyword; B keyword + conversational; C = B + claim paths.

**Evidence unit:** one message (observation). A system returns a ranked list of unique observations, cut at k.
**A path of n hops counts as its supporting observations, each using one slot.** The same budget applies to A, B and C.
An observation supporting several hops uses one slot. Scope: every thread (one user's memory).

| Metric | Rule |
|---|---|
| Recall@k | gold in top k / gold. Questions with no gold are excluded from recall |
| Precision@k | gold in top k / k |
| Path completeness@k | every gold item in the top k. Reported on the multi-hop class |
| Primary measure | multi-hop recall@10, C minus B, on development; target at least 10 points. Sealed questions reported separately |
| Added / displaced | gold in C's top k and not B's; gold in B's top k and not C's |

**Integrity checks, per question, on C. Each counts as pass or fail:**
| Check | Passes when |
|---|---|
| `overlap: [labels]` | every two-hop path over the question's gold has one of these overlap labels |
| `not_confirmed` | no path over the gold says `confirmed` overlap |
| `structured` | `query_by_name` (semantics v2) gives one of the listed answers |
| `tier: {key: tier}` | the key's observation appears with this tier when returned |
| `originator: {key: label}` | the returned item names this originator |
| `pending: {key: other}` | when `key` is returned, it carries a pending retraction note citing `other` |
| `ambiguous: name` | the result reports the name as ambiguous |
| `no_merge: [name]` | no path passes through two referents with this label as if one |
| `no_path: [[a, b]]` | no path connects these labels |
| `no_path_established: [[a, b]]` | no path connecting these labels has all hops accepted with overlap `confirmed` or undated. A path reported as `qualified` or incomplete is allowed |
| `gap: event` | not a pass or fail: records that a withheld one-time event blocks retrieval, for Phase 8C |

**Severe failures (must be zero):** an unresolved or qualified item shown as accepted; a `confirmed` overlap the
temporal evidence does not support; two distinct people merged; a path with a hop that has no evidence.

**Latency:** p50 and p95 per question over the world, measured with no other load.
