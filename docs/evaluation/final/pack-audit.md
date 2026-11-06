# Final evaluation: audit of the answer pack

**Result: no independent answer pack exists, so the final evaluation cannot be run as specified.** Nothing was generated, and no held-out text was read. Counts here are aggregates of dataset labels.

**Frozen baseline:** `54803afa5b0ce2684bb4cb67316af6ec3e8e0f3b`, on `feature/phase-8g-activity-replication`. 892 passed, 19 expected failures, 0 skipped, clean working tree. `main` is `6db22d4`. All branches match their remotes.

## What exists
| Item | State |
|---|---|
| Authoring brief | written, [never sent to an author](../phase-8c/independent-authoring-brief.md) |
| Delivered pack | **none**, in the repository, private folders or Downloads |
| Answer protocol | [written, never run](../phase-8d/evaluation-protocol.md) |
| Frozen external set | 135 third-party questions from two held-out conversations; question hashes and gold turns only |
| Answer scoring code | offline and tested, but it has no run command, and nothing feeds it real evidence |

## Coverage against the eight required categories
| Category | Frozen set (135) | Other held-out, same conversations | Outside-author pack, as briefed |
|---|---|---|---|
| Factual recall | none | 197 single-hop | not a category |
| Relationships | unlabelled, within multi-hop | | 10 |
| Multi-hop | 68 | | not a category |
| Historical change | none | | 10 |
| Temporal status | 67, time-of-event, not current-status | | 10 |
| Contradictions and corrections | none | | 10 |
| Evidence provenance | none, though citations can be scored on any question | | 10 |
| Unknown or unsupported | none | 102 adversarial | some, not a category |

The frozen set covers two of eight categories. The third-party dataset holds no contradiction, correction, retraction or provenance questions at all.

## Independence
| Source | Author independent of GUPI? | Concern |
|---|---|---|
| Frozen external set | yes | Selected mechanically by label. Held-out retrieval aggregates were seen in Phases 5 and 6D; no held-out conversation has been extracted by Claude. Licence unresolved, so results stay internal |
| Development questions | yes | **Contaminated:** both conversations informed Phases 8A to 8G |
| Second dataset | yes | 71 held-out update questions and 25 abstention questions, but each question has its own history, median 491 turns. Extraction across them is not feasible by hand |
| Outside-author pack | would be | The brief's categories reflect what GUPI was built for, so its framing may favour structure, however independent the author is |
| Anything written here | **no** | Development use only, and never called independent |

## Execution
| Requirement | State |
|---|---|
| Condition A, raw | supported by frozen retrieval |
| Condition B, raw + claims | **evidence export missing.** `condition_block` is tested, but nothing turns accepted claims into its `facts` |
| Condition C, governed | **same gap**, and notes must come from stored status, disputes and attribution |
| Extraction on held-out text | not yet done. The written rules forbid manual extraction there, and the frozen run needs the owner's approval flag |
| Fixed answering model | the code names `gpt-4o-mini`, a paid model. Claude would replace it, and must be recorded |
| Same conditions in sessions | no fixed temperature or output cap. One session holding many questions lets evidence leak between them |
| Judging | the protocol requires a person to check at least 30 model judgements |
| Clean contexts | subagents receive cached memory (Phase 8G), so answering needs audited fresh sessions |

An export script would be evaluation tooling, not a GUPI capability, but it still decides what structured evidence looks like, so it needs approval before results exist.
