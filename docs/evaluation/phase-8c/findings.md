# Phase 8C findings: what claims do on real conversations

**Development data, extracted by hand, inside a subscription. No paid calls. Not a benchmark or leaderboard result, and not a
`gpt-4o-mini` result.** Questions: 38 multi-hop and 63 temporal, from `conv-26` and `conv-30`. The extractor saw no questions.

## Real conversations
| Multi-hop (38) | R@5 | R@10 | R@100 | complete@10 |
|---|---:|---:|---:|---:|
| A keyword | 0.146 | 0.190 | 0.452 | 0.000 |
| B conversational | 0.207 | 0.320 | 0.595 | 0.079 |
| **C claim traversal** | **0.209** | **0.336** | **0.601** | **0.132** |
| D text-only names | 0.141 | 0.255 | 0.558 | 0.026 |

| Paired gain on multi-hop, points (95% interval) | R@5 | R@10 | R@100 |
|---|---:|---:|---:|
| C over B | +0.2 (−4.6 to 5.0) | +1.7 (−1.7 to 5.7) | +0.7 (0.0 to 2.0) |
| C over D | +6.8 (2.2 to 12.3) | +8.1 (2.2 to 15.6) | +4.4 (−2.6 to 11.8) |

**Result: not shown, at any depth,** under the pre-registered rule. C beats the name control, but not B. C+ (labelled session
links) added nothing: only one link was found. C found 3 gold turns in its top 5 that neither B nor D had.

| Temporal (63) | R@5 | R@10 | R@100 |
|---|---:|---:|---:|
| A keyword | 0.762 | 0.825 | 0.937 |
| B conversational | 0.794 | 0.857 | 0.968 |
| C claim traversal | 0.794 | 0.857 | 0.968 |
| D text-only names | 0.810 | 0.841 | 1.000 |

C equals B on temporal questions at every depth, with a mean gain of 0.

**Integrity:** 0 severe findings. All 5 two-hop overlap labels were `unknown`, none invented. Evidence correctness is not yet
independently verified.

**Latency:** C p50 110 ms, p95 147 ms; B 57 ms and 76 ms.

## Synthetic fixture (separate, developer-written, Phase 8B development questions)
| Multi-hop (11) | R@5 | R@10 | complete@10 |
|---|---:|---:|---:|
| A keyword | 0.667 | 0.742 | 0.455 |
| B conversational | 0.621 | 0.697 | 0.364 |
| C claim traversal | 0.712 | 0.879 | 0.727 |
| D text-only names | 0.576 | 0.879 | 0.727 |

Rankings are identical to 8B after this phase's changes. The sealed questions were not re-run.

**The contrast is the finding.** On a fixture full of named people and companies, C adds 18 points at R@10. On real chat, it adds
under 2. **A synthetic traversal success says little about real memory,** as the brief warned.

## Why traversal did little
| Graph measure | Result |
|---|---:|
| Claims formed | 123 |
| Claims linking two things | **5 (4.1%), below the 10% gate** |
| Referents | 14 |
| Turns with a claim | 14% |
| Gold turns with a claim | 36% |
| Claims sharing a referent with another session | 118 of 123, nearly all through the speaker |

The graph is two stars, one around each speaker. Connecting every claim to the same person tells retrieval very little.

## Exploratory: claims as a signal, not a graph
**The idea came from these results, so this is a hypothesis, not evidence.** Every variant has a text-only control.
| Multi-hop (38) | R@5 | R@10 | R@100 |
|---|---:|---:|---:|
| B conversational | 0.207 | 0.320 | 0.595 |
| Promote claim turns | 0.190 | 0.308 | 0.647 |
| Promote text-filter turns (no model) | 0.207 | 0.333 | 0.643 |
| Add all claim turns | 0.141 | 0.275 | 0.658 |
| Add all text-filter turns (no model) | 0.148 | 0.275 | 0.597 |

**A free text filter did about as well as claims when promoting.** Adding claim turns scored highest at depth 100, but it lowers
the top of the list, and it's one post-hoc result on 38 questions. Promoting the text filter also took temporal R@100 from
0.968 to 1.000. That's the one cheap retrieval idea worth testing on a fresh set.

## Evaluation criteria
| # | Question | Answer so far |
|---|---|---|
| 1 | Does extraction create a connected graph? | **No.** Connected through speakers only; 4.1% of claims link |
| 2 | Does traversal find what text misses? | **Barely.** 3 gold turns, and not shown overall |
| 3 | Does it rank better on tight budgets? | **Not shown.** +0.2 at R@5, and 8B's R@5 gain did not repeat |
| 4 | Do qualifications improve answers? | **Unknown.** Needs answers, not yet run |
| 5 | Is it worth the cost? | **Not for retrieval.** On this evidence, claims don't pay for extraction through recall |

## Can this architecture support competitive retrieval?
**Yes as a platform, but not because of claim traversal, and not yet.**

| | Assessment |
|---|---|
| **The foundation** | Sound. TypeDB handles scoped retrieval, bounded queries and full provenance at acceptable speed |
| **Where it falls short** | **Recall.** Multi-hop R@100 is 0.60, so 40% of evidence is missed, even with AML's generous depth. Questions that share few words with their evidence are the likely gap, which keyword search can't close. AML's open-source division requires `text-embedding-v4`, which GUPI lacks. The top open-source Cycle 1 textual entry's repository is named `vanilla-rag-memory`, a hint that plain retrieval may go far, though I have not read its method |
| **Where TypeDB could win** | Not finding text, but **knowing what to believe.** AML scores memory governance (updates, conflicts, deletion) and temporal reasoning. Those are what GUPI's evidence model is for. **It is unmeasured on any independent set** |

## Recommended next milestone
**A revised 8D, "Governed memory": measure what TypeDB is actually for, at no cost.** In order:
1. **Independent pack.** The authoring brief is ready: provenance, identity and temporal questions. This is the priority, and it
   needs an outside author.
2. **Parser and formation P2, P3, P4** ([coverage](coverage-analysis.md)), once approved. They add real structure: kinship, stable
   family referents and dated events.
3. **Answer-level test inside the subscription,** on that pack: the same evidence with and without GUPI's qualifications. That
   finally answers criterion 4, the strongest remaining case for TypeDB.
4. **Topic links, as a design only:** can repeated `object-text` connect claims across sessions, without new entity types?
   That's the one remaining route to a real graph on chat.

**Stop condition:** if qualifications don't improve correctness on the independent pack, keep GUPI simple: raw memory with strong
retrieval, plus a small evidence layer, and drop automated claim extraction from the AML path.

**Defer:** paid `gpt-4o-mini` extraction, batching, and any leaderboard adapter. Separately, recall needs a free plan: a local
embedding is the existing option, but it wouldn't be AML-eligible in the open-source division.

## Limitations
- 38 and 63 questions from two conversations, so intervals are wide.
- These conversations were used in Phases 8A and 8B.
- The extractor is the builder, and knows the parser's rules; a real model would likely do worse.
- LoCoMo is casual chat between two friends. Work conversations, with more named people, may link far more. That's untested, and
  worth knowing, because AML's other sources differ.
- `conv-26` and `conv-30` have few third parties, so identity (C+) was barely exercised on real data.
- Manual extraction consumed subscription usage and cannot scale.
