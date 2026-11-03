# Phase 5: offline evidence retrieval on LoCoMo and LongMemEval

**These are evidence-retrieval results, not LoCoMo or LongMemEval scores.** Those benchmarks grade generated
answers (LongMemEval with an LLM judge); GUPI generated no answers here. Datasets, licences and checksums:
docs/datasets.md. Protocol and amendments: benchmarks/config.json and ADR 0008. Every held-out
configuration below was run once; files here are those first runs, unchanged.

Metric: recall@k = share of the gold evidence units in the top k; MRR = 1/rank of the first gold unit
(within the top 50). LoCoMo unit: turn (6 questions without evidence ids excluded; 8 evidence ids in the
data do not match any turn). LongMemEval units: session and turn (`has_answer`).

## Held-out results (first run)
LoCoMo, 8 conversations, 1,676 scored questions, turns:

| System | R@5 | R@10 | MRR | median latency |
|---|---|---|---|---|
| keyword | **0.502** | **0.565** | **0.416** | 0.05 s |
| hybrid-unfiltered | 0.469 | **0.565** | 0.368 | 0.12 s |
| hybrid (structure-filtered) | 0.428 | 0.511 | 0.350 | 0.19 s |
| embedding | 0.363 | 0.465 | 0.270 | 0.07 s |
| structured | 0.011 | 0.038 | 0.015 | 0.07 s |

LongMemEval S, all 447 held-out questions (no embeddings):

| System | Session R@5 | Session MRR | Turn R@5 | Turn MRR |
|---|---|---|---|---|
| keyword | 0.890 | 0.903 | 0.683 | 0.652 |
| structured | 0.000 | 0.000 | 0.000 | 0.000 |

LongMemEval S, the pre-registered 64-question held-out subset (all systems):

| System | Session R@5 | Session MRR | Turn R@5 | Turn MRR | median latency |
|---|---|---|---|---|---|
| embedding | **0.933** | **0.922** | 0.618 | 0.542 | 0.07 s |
| hybrid / hybrid-unfiltered (identical) | 0.923 | 0.892 | **0.685** | **0.640** | 0.16-0.19 s |
| keyword | 0.836 | 0.854 | 0.653 | 0.603 | 0.13 s |
| structured | 0.000 | 0.000 | 0.000 | 0.000 | 0.03 s |

Development results (`*-dev*.json`) showed the same orderings.

## By category (held-out recall@5)
LoCoMo: keyword / embedding / hybrid / hybrid-unfiltered / structured
- adversarial (375): 0.588 / 0.460 / **0.272** / 0.565 / 0.000
- multi-hop (239): 0.154 / 0.140 / **0.200** / 0.184 / 0.004
- open-domain (78): 0.241 / 0.174 / 0.180 / 0.193 / 0.003
- single-hop (727): 0.579 / 0.396 / 0.567 / 0.514 / 0.019
- temporal (257): 0.561 / 0.394 / 0.553 / 0.546 / 0.012

LongMemEval subset, session recall@5 keyword / embedding / hybrid: knowledge-update (13) 0.962 / 1.000 / 0.962;
multi-session (15) 0.767 / 0.927 / 0.918; temporal-reasoning (15) 0.700 / 0.789 / 0.789; abstention (3)
0.667 / 1.000 / 1.000; single-session (18) all high. Full held-out keyword: temporal-reasoning 0.860,
knowledge-update 0.992, multi-session 0.830, abstention 0.58-0.90.

## Why structured retrieval did poorly
- **Nothing to structure.** The offline rule extractor found **0 claims** in LoCoMo's natural chat (it was
  written for a few organisational phrasings), so structure-only retrieval had only authorship and names.
- **No entity handle in LongMemEval.** Questions are about "I" and "my"; no named entity matches a referent
  in 430 of 447 questions, so the structured retriever returns nothing by design.
- **Structure without relevance.** In LoCoMo the question usually names one of the two speakers, so "turns
  by or naming X" is about half the conversation, ranked newest first: structure narrows, it does not rank.
- **Adversarial questions invert the filter.** LoCoMo's adversarial questions attribute an event to the wrong
  speaker; filtering to that speaker removes the true evidence (hybrid 0.272 vs 0.565 unfiltered).
- **Where it helped:** multi-hop questions (hybrid 0.200 vs 0.184 unfiltered and 0.154 keyword), the only
  category where the structural filter added recall.

## Why keyword retrieval was strongest on LoCoMo
LoCoMo questions reuse distinctive words from their evidence (activities, objects, names), turns are short,
and both speakers share a vocabulary-rich but small conversation, which suits BM25. The small local embedding
model handles paraphrase but blurs distinctive terms in short chit-chat turns. They are complementary: on
held-out LoCoMo, keyword alone found evidence in the top 5 for 386 questions where embedding did not, and
embedding alone for 150. On LongMemEval, where sessions are long and questions paraphrase their evidence,
embedding was best at session level and the hybrid at turn level.

## Cost and footprint
| | LoCoMo held-out | LongMemEval held-out (all) | LongMemEval subset |
|---|---|---|---|
| turns ingested | 5,094 | 220,178 (21,262 session versions) | 31,839 |
| ingestion | 45 s (113/s) | 1,268 s (174/s) | 160 s (199/s) |
| embedding | 92 s (56/s; short turns) | not run | 3,536 s (9/s; long turns) |
| database size | 59 MB | 815 MB | 359 MB |
| peak Python memory | 0.6 GB | 2.5 GB (JSON parsing) | 2.5 GB |

Embedding benchmark (`embeddings.json`): bge-small generates 177 short / 23 medium / 8.6 long texts per second
on this laptop's CPU; a stored vector is 2,048 characters; reading 50,000 vectors from TypeDB takes 4.8 s,
exact cosine over them 0.5 s with NumPy and 1.6 s in pure Python (same top 10); writing runs at about 290
vectors/s. Exact search is fine for per-question scopes but would need TypeDB native vectors (or another
index) for whole-memory search at scale.
