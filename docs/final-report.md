# GUPI final research report

**Status (2026-11-09): research paused.** **Recommendation: pause development until there is a more suitable use case or stronger evidence.** GUPI's evidence model is sound. But we haven't shown that it improves an agent's answers, or that TypeDB gives it a measurable advantage.

**The final answer-level evaluation was not run.** No independent answer pack exists, and the owner chose to close without one ([audit](evaluation/final/pack-audit.md)). **So the central question is unanswered: does TypeDB-backed structured memory make an agent's answers more correct than conventional retrieval?** Every answer-level result below is from development material.

**Baseline:** `54803afa5b0ce2684bb4cb67316af6ec3e8e0f3b` (`feature/phase-8g-activity-replication`). 892 tests passed, 19 expected failures, 0 skipped, with TypeDB 3.14.1. Lifetime API spend: $0.

## A. What we built
| Layer | What it is | Where |
|---|---|---|
| **Evidence** | sources, verbatim observations, exact evidence spans, authorship | `memory.py`, `records.py`, `core/0001`, `0009`, `0011` |
| **Claims** | one typed claim per attestation, as a TypeDB relation with roles. Polarity, commitment, attribution and allegation are kept, never flattened | `core/0001`, `0010`, ADR 0001 |
| **Governance** | review queue; reviewable supersession, which can be withdrawn; alternative readings; conflicts that separate contradiction from differing evidence; identities merged only once accepted | `review.py`, `conflicts.py`, `identity.py`, `core/0004`, `0005` |
| **Time** | bitemporal: valid time and belief time are separate. Answers are TRUE, FALSE, PRESUMED, UNKNOWN, NOT_YET_KNOWN or CONTESTED, by spell semantics, never guessing a date | `answering_v2.py`, `temporal.py`, `timeexpr.py`, ADR 0003, 0009 |
| **Extraction** | rule extractor; model contract `model:candidate-v1.1` with a strict parser; candidate store; formation policy that prefers review to formation; offline replay of recorded model output | `extraction/`, `formation/`, `core/0012` |
| **Events** | dated `event-statement`, separate from continuing states | `events.py`, `core/0013`, ADR 0010 |
| **Retrieval** | keyword, local embedding (stored in TypeDB, searched in Python), structured open-role questions, conversational context, and bounded claim-path traversal | `retrieval.py`, `query.py`, `explore.py`, `paths.py` |
| **Schema** | 13 additive core migrations plus a `people` pack: 11 entity, 23 relation and 50 attribute types, and 6 functions. Every value is a query parameter | `src/gupi/schema/` |

Most of the reasoning runs in Python over data fetched from TypeDB. Answer semantics, temporal reading, qualification and conflict detection hold almost no TypeQL. Filtering, open-role questions and path traversal run in TypeDB.

## B. What works
| Capability | Evidence | Strength |
|---|---|---|
| **Evidence integrity** | Every quote is checked word for word. Stage 4 stopped all 3 formed severe errors on the frozen Stage 3B responses: all go to review | strong in tests, on a small set |
| **Bitemporal answers** | 13 of 15 end to end with 0 unsupported definitive answers, against 5 of 15 for a keyword heuristic, on D1 (Phase 6D). The 2 misses are more cautious, not wrong | **development only**: D1 was written by the implementer |
| **Governance** | review, supersession, disputes and retractions behave as specified, with history intact | tests and invented fixtures |
| **Model-assisted extraction** | Stage 3B: recall 21 of 39 against 3 of 39 for rules, precision 21 of 30 | exploratory corpus, model-assisted adjudication |
| **Conversational retrieval** | LoCoMo development R@10 0.587 → 0.698 (Phase 8B). Phase 8C multi-hop R@10: keyword 0.190, conversational 0.320 | development data |
| **Safety under ambiguity** | no severe integrity finding in 8B, 8C or 8D; overlaps left `unknown` rather than invented | development data |

## C. What does not work
| Problem | Evidence |
|---|---|
| **Claims don't add recall on real chat** | 8C multi-hop, claims over conversational retrieval: R@5 +0.2 (−4.6 to 5.0), R@10 +1.7 (−1.7 to 5.7). Not shown. In 8B a text-only name control equalled claims at R@10 |
| **Extraction is sparse on chat** | 279 assertions in 788 turns, 123 formed. Only 5 claims (4%) link two named things, because people talk about hobbies and plans more than relationships |
| **Structure hurt where questions mislead** | Phase 5 adversarial R@5: structured hybrid 0.272 against 0.565 unfiltered |
| **Retrieval on independent data** | Phase 6D: 0 candidates from 5,094 LoCoMo and 220,178 LongMemEval held-out turns with the rule extractor. Phase 5: keyword beat structured retrieval overall |
| **Temporal over-assertion** | "since March" read as a start date ([known issues](known-issues.md)). An undated start then an end stays unknown. A past-tense mention closes an activity that's still going. Asked after a conversation ends, the classifier can't say "still engaged" |
| **Activity memory** | 8F and 8G: final-state agreement 0.71 then 0.16; readers found 9 to 47 activities; the classifier's agreement gain was mostly mechanical. Not implemented |
| **Semantic ambiguity** | Two judges using one rule split on "still continues" in 56 of 132 cases. Granularity has no right answer |
| **Scale** | vectors are base64 strings, searched exactly: 50,000 in 5.3 s. No native vector index in TypeDB 3.14.1 |
| **Independence** | Every favourable answer-level result is on material written by the builder. Outside annotators, authors and a human judge were never found |

## D. Benchmark results
| Comparison | Data | Sample | Result |
|---|---|---:|---|
| Retrieval: keyword, embedding, hybrid, structured (Phase 5) | LoCoMo held-out, first run | all held-out | keyword turn R@5 0.502, structured 0.011 |
| Same (Phase 5) | LongMemEval held-out | 447 | keyword session R@5 0.890; structured 0 |
| End-to-end answers (Phase 6D) | D1, developer-written | 15 | GUPI 13, keyword heuristic 5. **Not independent** |
| Claim traversal over conversational retrieval (8B) | invented fixture, sealed | 5 | R@10 0.900 both; R@5 0.900 against 0.800 |
| Same (8C, 8D) | real development chat | 38 multi-hop | no significant gain at any depth |
| Activity consolidation (8F, 8G) | two development conversations | 9 ledgers, 4 judges | evidence 100% valid; structure partly reproducible; states not |
| **Answer quality, structured against raw** | **none** | **0** | **not tested** |

Intervals are paired, seeded bootstraps where given. All of these readers and judges were Claude models, apart from 19 adjudication cases reviewed by a different vendor's model.

## E. TypeDB's contribution
**No result shows TypeDB delivering measurably better answers or recall.** Storing the data in TypeDB is not itself a benefit, so I credit it only where the typed model did work.

| Capability | Does TypeDB add value? | Could PostgreSQL or application code do it? |
|---|---|---|
| **Claims as n-ary relations with roles** | **Yes, in modelling.** Attestation, attribution, allegation and roles live in one typed relation. Schema checks role players and the `people` pack's types | Yes, with join tables and checks, but less directly and less safely |
| **Path traversal with type constraints** | **Not measured as better.** It's bounded and readable, but it equalled a text name control in 8B and didn't beat conversational retrieval in 8C | Yes: recursive CTEs or application graph code |
| **Bitemporal reasoning** | **No.** It's Python | Yes, and SQL temporal tables are mature |
| **Provenance and governance** | **Modest.** Typed review and supersession relations keep history explicit | Yes, with audit tables |
| **Open-role questions with filtering in the database** | **Some convenience.** Readable queries with type inheritance | Yes |
| **Vectors** | **A cost.** No native type or index | Better, with pgvector |
| **Migrations and safety** | neutral. Parameters everywhere; additive schema | neutral |

**Inconclusive:** whether TypeDB's typed relations would matter on data that is dense in relationships, such as enterprise records, industrial assets or robotics state. There, connections are explicit, so extraction doesn't throttle them. Chat had too few connections to test traversal.

**Friction logged:** a 3.14.1 planner bug in a disjunction pattern, which was worked around; no vector type; Python round trips for most reasoning.

## F. Future directions (options, not commitments)
| Direction | Assessment |
|---|---|
| **1. General-purpose conversational memory** | **Weakest fit.** Chat is sparse in relationships, and text retrieval is strong and simpler. Structure has shown no recall gain, and answer gains are untested. A strong embedding or keyword system will be hard to beat |
| **2. Domain-specific structured agent memory** (industrial, robotics, enterprise) | **Most promising for TypeDB.** The entities, relations and typed constraints already exist in the source data, so the main bottleneck here, extraction, mostly disappears. Bitemporal state and provenance of sensor or system facts matter. Untested |
| **3. Governed evidence management for agents** | **Most promising for GUPI's existing work.** Provenance, disputes, retractions, allegations, review and belief time are the parts that worked. The value is trust and auditability rather than accuracy, so the test is safety and compliance, not leaderboard recall |

## G. Recommendation
**Pause development until there is a more suitable use case or stronger evidence.**
- **Why not continue:** there is no convincing evidence of differentiated value. Answer quality is untested, claims added no recall on real chat, and activity memory failed replication.
- **Why not reconsider the architecture:** the evidence and governance layer did what it was designed to do in every test. The failures are in fit to chat data and in temporal reading, and nothing shows the core model to be wrong.
- **What would justify resuming:** an independent answer pack (the brief is in [phase-8c](evaluation/phase-8c/independent-authoring-brief.md)), or a domain with dense explicit relationships where direction 2 or 3 can be tested against a relational baseline.

## Reproduction
```bash
docker compose up -d && uv sync
uv run pytest -q
uv run python -I -m gupi.benchmarks.phase8c_eval run --set dev --conversations conv-26 conv-30 --responses ../gupi-phase8c-private/responses/dev-8d.jsonl --json OUT.json
uv run python -I -m gupi.benchmarks.phase8f_agreement compare --conversation conv-26 --ledgers A=... B=... C1=... C2=... --json OUT.json
uv run python -I -m gupi.benchmarks.phase8g_replication verdict --agreement docs/evaluation/phase-8g/results/8g-agreement.json
```
Datasets go in git-ignored `.data/` ([datasets](datasets.md)). Recorded responses, ledgers and judgements are private and are not distributed. Each phase's README gives its own commands.
