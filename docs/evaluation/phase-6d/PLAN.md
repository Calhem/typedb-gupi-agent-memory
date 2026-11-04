# Phase 6D end-to-end evaluation: protocol (frozen before any run)

Committed with `manifest.json` before the runner existed. Nothing in production extraction, formation,
answering, schemas or migrations changes in this phase. The frozen fixtures, gold answers and earlier
results are read, never edited.

## What is evaluated
| System | What it produces | Kind |
|---|---|---|
| **GUPI end to end** (`gupi-e2e`) | `rules:v2` → validation → candidate store (`store.submit`) → `formation:v1` → TypeDB claims → v2 answers with qualification and citations | **answers** |
| GUPI end to end, policy only (`gupi-e2e-policy`) | the same, with no simulated candidate reviewer (identity decisions still applied) | answers |
| GUPI on gold claims (`gupi-gold`) | the Phase 4 configuration: gold claims, gold review decisions, v2 answers. An upper bound for extraction, not a baseline | answers (diagnostic) |
| GUPI Phase 4 pipeline (`gupi-rules-v1`) | `rules:v1` → claims → simulated review → v2 answers (existing configuration) | answers (diagnostic) |
| Keyword answer baseline (`keyword-answer`) | the existing Phase 4 heuristic in `gupi.retrieval_eval.keyword` | answers |
| Keyword (`keyword`) | BM25 over original passages (`gupi.evidence.keyword`) | **evidence only** |
| Embedding (`embedding`) | cosine over bge-small-en-v1.5 embeddings stored in TypeDB (`gupi.evidence.embedding`) | evidence only |
| Hybrid (`hybrid`, `hybrid-unfiltered`) | the Phase 5 pre-registered fusion, with and without the structural filter | evidence only |
| Structured (`structured`) | the Phase 5 structure-only retriever, run over the end-to-end database (so it sees `rules:v2` claims) | evidence only |
| Flat-triple / claim-node baseline | **not evaluated**: no fair implementation exists in the repository, and building one is out of scope | — |

Evidence-only systems get **no answer accuracy** ("not evaluated"); their retrieval is never presented as
answer accuracy. GUPI's citations are an unranked set of messages, so for GUPI only set precision and
recall are reported, never recall@k.

## Datasets (versions and hashes in manifest.json)
| Id | Material | Layers | Prior use |
|---|---|---|---|
| D1 | Phase 4 frozen world and 15 questions (`tests/fixtures/retrieval`) | A, B, C, D | written by the implementer (Phase 4); answer semantics v1 and v2 were developed and reported with it (v2 13/15); `rules:v2` was **not** written against it. Not independent for answering. |
| D2 | Phase 2 held-out conversations (`tests/fixtures/conversations/heldout`, 12 messages, 12 gold claims) | A | written before any extractor; `rules:v2` held-out recall (type, participants, polarity) already reported once in 6B (5/12). No questions or answers exist, so answers are not evaluated. |
| D3 | Phase 6B frozen extraction set (`tests/fixtures/formation/eval-v1.json`, 32 passages) | A | written by the implementer just before `rules:v2`, with its scope in mind; first run reported in 6B. Development-adjacent: flatters the extractor. |
| D4 | Phase 6C adversarial cases (`adversarial-v1.json`, 17 cases) | A, C | **development tests**, written by the designer of the qualification. Never treated as independent evidence. |
| D5 | LoCoMo held-out (8 conversations, 1,986 questions; split in benchmarks/split.json) | A, B, D | Phase 5 held-out first run (retrieval) already reported; second exposure, no tuning. Licence CC BY-NC 4.0: research use, no content committed. |
| D6 | LongMemEval S cleaned, held-out (447 questions); TypeDB run on the pre-registered 64-question subset | A, B, D | Phase 5 held-out first run already reported; MIT. |

Not used: specialist M1 material (M1 has not been conducted), the Phase 2 development split,
LoCoMo and LongMemEval development splits (except the feasibility slice), any new download.

**Pre-manifest probe (disclosed):** before this protocol was written, a timing probe ran `rules:v2` over
LoCoMo turns in memory (dev 788 turns, held-out 5,094): 0 candidates in both, 0.17 s. Nothing was changed
as a result; it is why LoCoMo retrieval for GUPI is expected to equal the structure-only retriever.

## Simulated reviewer for D1 (fixed here, before any run)
The world records review decisions per message (accepted unless `rejected` or `unreviewed`). For each
stored candidate of message *m*, matched to *m*'s gold claim by claim type and role names (case- and
space-normalised):
- status **review**, gold accepted → `store.review(approve)`; gold rejected or **no matching gold claim** →
  `store.review(reject)` (a careful reviewer refuses a wrong extraction); gold unreviewed → no decision.
- status **formed** (accepted by the policy), gold rejected → the claim is rejected with `Memory.review`;
  otherwise no decision. A formed candidate that matches no gold claim is left as formed: no reviewer saw it.
- status **withheld** → no decision.
Same-name identities are accepted on 2025-09-01, as in Phase 4, for every GUPI configuration.
Clock: the message is received one hour after it was said (submit), reviewed two hours after.

## Measures and scoring rules
**A. Formation.** One-to-one greedy matching by claim type + role surfaces (+ polarity for D3), as in
`gupi.formation.evaluation`. Reported with numerators and denominators: candidate precision and recall;
participant (entity) precision and recall against gold mentions (D2); relation accuracy = role assignment of
matched candidates; temporal accuracy on matched claims: the stored claim's start window, end window and
ongoing-at-observation, each compared exactly with the gold (D1, D2; Phase 2 gold encodes "since X" as a
start, a known convention difference); polarity, modality, commitment, attribution (D3 with the frozen
scorer); policy outcomes formed / withheld / review / rejected (from the store's decision records); and
representation: each gold claim is an **accepted claim** in TypeDB, a **stored candidate only**, or
**absent**.

**B. Retrieval.** recall@1/5/10 = share of gold evidence units in the top k; precision@5 = gold units in the
top 5 / 5 (the denominator is fixed at 5; for D1, at most 2 gold units exist, so it is low by construction);
by category. For GUPI: whether each gold evidence message was cited, formed but not cited, a stored
candidate only, or text only. Units: D1 messages; D5 turns; D6 sessions and turns.

**C. Answers (D1, D4).** The frozen `gupi.retrieval_eval.score` (answer equals gold, binding equal for open
questions; abstention; unsupported assertions; citation precision and recall). Added, without changing it:
**missing** (the system raised an error or returned nothing) counted apart from **incorrect**; contradiction
(gold CONTESTED); belief-time questions; open-role questions; abstention; qualification standing of every
answer; unsupported definitive rate = definitive TRUE/FALSE where the gold is UNKNOWN, NOT_YET_KNOWN or
CONTESTED, or where any deciding evidence is not direct. D4 uses its frozen scorer
(`scripts/evaluate_adversarial.score`) through the candidate store. No LLM judge.

**D. Operations.** Extraction throughput; submit time; candidate, decision and claim counts; database size
(TypeDB data directory, `du`); ingestion time; query latency p50 and p95 per system; embedding time; peak
Python memory; incremental behaviour (resubmission writes nothing; per-message submit time and `pending()`
time as the store grows, on a synthetic load built by renaming the D3 passages: an operational probe only,
never scored for accuracy). Ingestion and query costs are reported separately.

## Failure attribution
For every incorrect or unsupported GUPI answer (and every answer whose citations miss all gold evidence),
the earliest responsible stage, from the trace: 1 source evidence absent; 2 extraction missed; 3 extraction
misinterpreted; 4 validation or formation withheld; 5 stored incorrectly; 6 retrieval missed stored
evidence; 7 temporal or evidential reasoning; 8 answer formatting or citation; 9 gold or evaluation
ambiguity. Assigned by fixed rules in the runner first; any manual reassignment is listed with its reason.
For D5/D6, each question's gold turns are classified for the GUPI structured arm (no candidate: out of the
extractor's domain vs an in-domain sentence not parsed; candidate stored; claim formed; retrieved).

## Execution
1. A **feasibility run** (labelled `feasibility`): D1, D4 and a 20-question LoCoMo dev slice, checking that
   the store is used, the intended database is queried, baselines see the same observations, missing and
   incorrect are distinguished, two runs agree, and no gold reaches a system.
2. The **first full run** (labelled `first-run`), preserved unchanged including failures.
3. Any later run is labelled separately and never replaces the first.
Defects found are documented with a regression-test proposal, not fixed.

## Cost
Local only: `rules:v2`, the already-downloaded bge-small model, TypeDB in Docker. No paid API, no new
download, no LLM judge. The $10 ledger is not touched.
