# GUPI capability register: existing, proposed, unproven

Date: 2026-11-03. "Existing" means implemented and covered by tests against the live TypeDB 3.14.1 server;
"proposed" means designed but not built; "hypothesis" means a claim about value that has not been shown.

## Existing (implemented and tested)
| Capability | Where | Evidence |
|---|---|---|
| Observations, claims (one per attestation), evidence spans, provenance | ADR 0001 | Phase 1 tests |
| Reviews, supersessions, alternatives as historical events; reversible corrections | ADR 0001, 0006 | Phase 1/3 tests; TypeDB and Python agree |
| Bitemporal answers TRUE/FALSE/UNKNOWN/NOT_YET_KNOWN/CONTESTED; same-spell rule; spell assembly | ADR 0003, 0006, 0007 | Phase 3/4 tests |
| Conflict classes (contradiction, differing evidence, corroboration, separate periods); domain constraints | ADR 0006 | Phase 3/4 tests |
| Suggested identities, merged only when accepted | ADR 0006 | Phase 3 tests |
| Structured questions with citations, exclusions, as-of name resolution | ADR 0007 | Phase 4 tests; frozen benchmark |
| Filtering in TypeDB (per-claim functions, bucketed conflicts) | ADR 0007 | latency flat to 6,000 claims |
| Rule-based offline extraction; validator rejecting ungrounded spans, dates and types | ADR 0005 | Phase 2 tests; held-out recall 0.50 |
| Budgeted Claude extractor (fail-closed ledger) | ADR 0005 | simulated client only; **never run live** |
| Keyword (BM25), local embedding and hybrid evidence retrieval; embeddings stored in TypeDB | ADR 0002, 0008 | Phase 5 tests and benchmarks |
| Migrations with backup and restore; review CLI | ADR 0004 | tests |
| Tense-aware dates: a month without a year resolved from tense or scheduling words, left unknown when ambiguous; explicit vs inferred dates recorded per claim | ADR 0005 amendment | regression tests; **in PR #1 (`fix/month-without-year`), not yet in `main`** |

## Known defects (found 2026-11-03; not fixed; see joined-spell-analysis.md)
| Id | Defect | Effect |
|---|---|---|
| D1 | A spell joined from two claims answers TRUE | presumption shown as direct truth; wrong when a gap went unrecorded |
| D2 | A recorded termination defeats any later reinstatement | FALSE instead of TRUE during a second spell |
| D3 | A reinstatement's start leaks FALSE into the earlier spell | FALSE instead of TRUE during a first spell |
| D4 | A "still true" claim without a stated start never holds | conflicts inside a recorded gap are reported as FALSE, not CONTESTED |

## Proposed (designed, not built)
Spell-based truth semantics v2 with a PRESUMED outcome, evidence-first classification and FALSE only on
negative evidence (v2-truth-semantics.md, proposed ADR 0009; fixes D1-D4, versioned so past results keep v1); the M1 evaluation pilot with Python-object, flat-triple, reified-triple and PostgreSQL
evaluation-only baselines and extraction-error injection (m1-protocol.md);
Memory Formation Engine stages: source documents, salience, support assessment, attribution and
modality, change analysis, schema-gap proposals, acceptance policy (memory-formation-engine.md);
`projects` domain pack and chronological benchmark (domain-and-evaluation.md); CronQuestions adapter;
Graphiti comparison; AVeriTeC support-decision evaluation.

## Hypotheses (not shown)
| Hypothesis | Current evidence |
|---|---|
| TypeDB's typed n-ary, temporal and provenance model gives more reliable answers about complex, changing, contradictory knowledge than text retrieval | **Partial, weak**: on the small synthetic Phase 4 world, structured answers beat a deliberately simple keyword baseline (13/15 vs 5/15 first run), but with oracle-quality claims and a world written by the same team |
| Structure helps evidence retrieval on conversational memory | **Not supported** by Phase 5: structure-only retrieval near zero on LoCoMo and LongMemEval; the structural filter lowered hybrid recall on LoCoMo |
| A formation engine can produce claims reliable enough for the structured path to pay off | **Untested**: offline rules extract nothing from natural chat; no live LLM extraction has been run |
| Separating salience, support and acceptance reduces unsupported confident answers | **Untested** (design only) |
| GUPI is competitive with temporal graph memory systems such as Graphiti | **Untested**; needs an approved LLM setting |
