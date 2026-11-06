# Phase 8A, part 1: current architecture and why structured retrieval underperformed

Inspected at `main` `6db22d4` (Stages 3A–4 merged; 579 passed, 19 expected failures, 0 skipped).
Labels: **confirmed** means read in the code or measured; **hypothesis** means not yet tested.
Probe scripts and raw aggregate output: [probes/](probes/).

## 1. The path from conversation to answer
| Step | What happens | Where |
|---|---|---|
| 1. Enter | a message becomes an immutable `observation` (verbatim text, `observed-at`, `received-at`), linked to its `source`, `context` and author | `core/0001`, `core/0009`; `memory.py:142` |
| 2. Extract | either the older `gupi.extraction` pipeline, which writes unreviewed hypotheses, or `rules:v2`/`model:candidate-v1.1`, which emit candidates | `extraction/pipeline.py`; `formation/rules_v2.py`; `formation/model_candidate.py` |
| 3. Admit | `form.decide` gives each candidate one outcome: formed, review, withheld or rejected. The candidate store keeps every decision | `formation/form.py:77`; `formation/store.py:88` |
| 4. Store | a formed candidate becomes a typed `claim` relation with `evidence`, an acceptance `review`, and mentions | `formation/form.py:196` |
| 5. Locate | text retrievers rank observations in a scope; structured questions look up one claim type with fixed roles | `evidence.py`; `search.py`; `query.py:146` |
| 6. Connect | `explore` walks believed claims; `follow` chains structured questions. **Neither is connected to text retrieval** | `explore.py:29`, `explore.py:77` |
| 7. Answer | `answering_v2.classify` gives the temporal answer; `qualification.qualify` gives the evidential standing separately | `answering_v2.py:54`; `qualification.py:59` |

## 2. What TypeDB stores today (confirmed)
| Relationship | Connects | Usable in a join today? |
|---|---|---|
| typed claims: `employment`, `reporting`, `statement`, `identity` | referents through named roles, with valid time and provenance | yes |
| `evidence` | claim → observation, with a span | yes |
| `sourcing`, `containment`, `authorship` | observation → source, context, author | yes, and populated for all benchmark turns |
| `mentioning` + `reference` | observation → mention → referent | yes, but **empty on the benchmarks**: mentions come only from extraction |
| `assertion` | claim → who asserted it | yes |
| `review`, `supersession`, `alternatives` | decisions on claims | yes; `believed_claim` uses them inside TypeDB |
| `candidate-of`, `formation-decision`, `formed-into`, `correction-suggestion` | candidates, decisions, targets | yes, but a candidate's content (participants, times) is **JSON in `candidate-payload`**, so it cannot be joined on |
| turn order within a context | – | **no relationship**: only `observed-at` |

**Everything joins in one query.** A two-claim path with belief filters ran on a disposable database in about 20 ms
as a first, uncached call (`probes/results-queries.txt`, Q5).

## 3. Where Python does work TypeDB could do
| Operation | Today | Move to TypeDB? |
|---|---|---|
| "Believed" status | **already in TypeDB** (`believed_claim`); Python mirrors it for explanations; tests keep the two in step | leave |
| Accepted identity groups | every question reads accepted identities and runs union-find (`identity.py:127`, `memory.py:398`) | only if identities become numerous. A recursive TypeQL function was **accepted by 3.14.1's `define`, but was not executed** |
| Multi-hop walk | one Python round trip per hop (`explore.py:42`) | **yes:** one bounded query per path shape |
| Finding entities in a question | loads every label in scope, then regex in Python (`evidence.py:83-90`) | no gain: a question is free text. Keep in Python, but cache per scope |
| Evidence for many claims | already one batched query (`retrieval.py:86`, `:208`) | leave |
| BM25 scoring | `contains` selects, Python scores (`evidence.py:38`) | leave: TypeDB has no text ranking |
| Temporal truth and spells | Python (`answering_v2.py`, `temporal.py`) | **leave.** It is multi-claim reasoning with windows; a TypeQL copy would be the competing model the brief forbids |
| Conflict buckets | already in TypeDB (`reduce count groupby`) | leave |

**Conclusion:** TypeDB is underused in one specific place, connecting claims at retrieval time. The Python temporal
and answering logic is correctly placed.

## 4. Why structured retrieval scored 0.000 (confirmed)
1. **No claims existed.** LoCoMo produced **0 claims** (`docs/evaluation/phase-5/locomo-dev.json`,
   `claims_extracted: 0`; Phase 7A confirmed 0 candidates from 252,632 turns). No claims means no graph.
2. **It had no relevance signal.** With no claims, ranking falls to newest-first over "turns by or naming the
   entity" (`evidence.py:110`). That is about half a conversation in recency order.
3. **Filtering backfired.** Hybrid is restricted to those candidates (`evidence.py:114-121`). Adversarial questions
   name the wrong speaker: 16% of their gold turns are by the named speaker, against 93–100% elsewhere.
4. **LongMemEval has no handle.** Questions say "I" and "my", so no entity matches and it returns nothing by design.

**So the score does not test TypeDB's relationship model at all.** It tests a retriever that had no relationships
and did not use the question's words. Neither "TypeDB does not help" nor its opposite follows from it.

## 5. Where relevant evidence is lost
| Loss | Kind | Evidence |
|---|---|---|
| Chat facts never become claims | **extraction** | Phase 7A: 31 of 39 sampled assertions are outside the typed domain |
| One-time events dated only to a period are withheld | **storage** (no mapping) | `validate.py:230`. "Meridian acquired Northstar in 2022" read as `holds-at` is withheld; see part 3 §3 |
| `event` and `occurred-at-*` exist in the schema but are unused | **storage** | abstract, no subtype; no Python writes them |
| Explicit-versus-inferred date flag | **storage** | `TimeEvidence.explicit` stays in the candidate JSON; a claim keeps only precision and bases |
| A bare retraction has no edge to what it retracts | **storage/extraction** | possible targets are a report flag only (`model_candidate.py:470`); a null-target suggestion links to nothing |
| Withheld and review candidates cannot be traversed | **storage**, by design | content is JSON; they stay findable as raw text |
| Claims are not connected to text results | **retrieval** | §1 step 6 |
| Gold evidence shares no word with the question | **retrieval** | 54% of LoCoMo multi-hop gold turns (development) |
| `evidence.keyword` ignores `received-at` | **retrieval defect** | `evidence.py:38` has no belief-time filter, unlike `search.py:48`; as-of retrieval must not use it unchanged |
| A statement's key ignores its predicate | **storage** (design) | `records.py:26`: "acquired" and "sued" between the same parties share a proposition key (measured). Questions separate them with `values`; `shared_keys_believed` does not, so false conflict buckets are possible (*hypothesis*) |

## 6. The seven questions in the brief
| # | Question | Finding |
|---|---|---|
| 1 | Useful relationships stored? | §2. Rich for formed claims; for benchmark chat only authorship, containment and time |
| 2 | Queryable together? | Yes, including claims, belief functions, evidence and provenance in one query |
| 3 | Python that TypeQL could do? | §3: mainly the hop-by-hop walk |
| 4 | Why was structured poor? | §4: no claims, no relevance signal, harmful filter |
| 5 | Is raw evidence retrievable? | **Yes.** Every turn is stored verbatim and searchable whatever extraction did; embeddings are optional |
| 6 | Do temporal records support constrained traversal? | Yes for reading (bounds are attributes), but truth needs whole spells, not single claims: see part 3 |
| 7 | What do evidence paths need? | Nothing new in the schema: one path query per shape, then existing views. See part 2 |

## 7. Checks against the brief's figures
| Item | Brief | Repository |
|---|---|---|
| Keyword / hybrid-unfiltered / hybrid-filtered / structured (LoCoMo development, R@5) | 0.513 / 0.444 / 0.414 / 0.000 | **match** |
| Embedding | 0.460 | **0.342** at R@5. 0.454 is its R@10 and 0.465 its held-out R@10, so 0.460 matches no committed figure |
| Stage 4 | merged, 579 + 19 | **confirmed** |
| "model.1 pipeline" (earlier brief) | – | no such name in the repository; read as `model:candidate-v1.1` |
