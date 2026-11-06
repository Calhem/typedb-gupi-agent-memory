# Phase 8C.3: independent evaluation protocol and scoring rules

**Frozen before any model reply exists.** Changing anything here after Gate 2 starts invalidates the run. Files:
`benchmarks/phase8c.json`, `benchmarks/phase8c-frozen.json`, `src/gupi/benchmarks/phase8c_eval.py`.

## Two sets, because neither source covers everything
| Set | Source | Size | Covers | Status |
|---|---|---|---|---|
| **External** | LoCoMo held-out `conv-41`, `conv-42`, chosen as the first two in sorted order | **68 multi-hop, 67 temporal** | multi-session relationships, time | **frozen** |
| **Independent pack** | written by someone who has not seen GUPI | at least 30 | provenance, identity, harder temporal | **needs an author** ([brief](independent-authoring-brief.md)) |

**Selection rule (mechanical):** every question labelled multi-hop whose evidence sits in two or more sessions, and every
question labelled temporal that has evidence. It uses only the dataset's labels, and I read no held-out text. To size
this, aggregate counts of category and evidence were computed across all held-out conversations.

**Why not the development conversations?** They have only 38 such questions, and they informed Phases 8A and 8B.

**LoCoMo has no provenance or identity questions, and few temporal questions cross sessions here.** The external set
cannot answer those parts of the brief alone. LoCoMo's licence is unresolved, so results stay internal.

**No AML held-out material is used.** The public LoCoMo file is the one already in `.data/`, by checksum.

## Comparisons
Same questions, scope, k, gold and scorer. Budget: `pool` 100, `keep` 3, `window` 1, `seeds` 5, `hops` 2, `max_paths` 50,
`hub` 100. Every system ranks to depth 100, and the top 5 and top 10 are prefixes of that one ranking.
| | System |
|---|---|
| A | keyword |
| B | A + conversational relationships |
| C | B + TypeDB claim traversal, accepted identities only |
| D | B + text-only name matching, the same merge as C |
| C+ | C + hypothesis session links, labelled (secondary) |

**The control was strengthened for chat.** 8B's treated any capitalised word as a name, so on chat "The" and "Yesterday"
would count, and that would flatter TypeDB. D now uses only words capitalised mid-sentence somewhere in the corpus,
stronger matches first.

## The decision rule
On the multi-hop stratum, at each of R@5, R@10 and R@100, **a gain is shown only if C beats both B and D by at least 5
points, and the 95% interval of each paired gain is above zero.** The interval is a seeded bootstrap over questions
(10,000 samples). Anything else is "not shown", with no re-analysis.

**Also reported, unchanged:** complete@k; every system by stratum; gold turns C found that neither B nor D did; latency.

## Reported separately
| Measure | Where | Note |
|---|---|---|
| Extraction coverage | `graph.turn_coverage`, gold turns with a claim | |
| Claim admission | `tally.decisions`, `tally.outcomes` | formed, review, withheld; each stop reason |
| Graph connectivity | `graph` | linking share, components, claims reaching another session |
| Evidence correctness | a random sample of 100 formed claims | **not verified until someone other than the builder judges it** |
| Temporal integrity | `overlap_labels`, integrity checks | no gold labels exist on LoCoMo, so these are counts plus must-be-zero checks |
| Must-be-zero | `summary.severe` | uncertain shown as accepted; out of scope; no evidence; unconfirmed shown as firm |

## Baseline with no claims (development, free)
[results/8c-dev-baseline-no-claims.json](results/8c-dev-baseline-no-claims.json). Claims: 0, so C equals B by construction.
| Multi-hop (38) | R@5 | R@10 | R@100 |
|---|---:|---:|---:|
| A keyword | 0.146 | 0.190 | 0.452 |
| B conversational | 0.207 | 0.320 | 0.595 |
| D name control | 0.141 | 0.255 | 0.558 |

| Temporal (63) | R@5 | R@10 | R@100 |
|---|---:|---:|---:|
| A keyword | 0.762 | 0.825 | 0.937 |
| B conversational | 0.794 | 0.857 | 0.968 |
| D name control | 0.810 | 0.841 | 1.000 |

**Read with care:** D is below B on multi-hop, so on this data the test that matters is C against B. Temporal recall is
already high, so there is little room for C there.
