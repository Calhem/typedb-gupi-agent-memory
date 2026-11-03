# Specialist benchmark assessment

Date: 2026-11-03. Purpose: find external benchmarks that test what GUPI's specialist direction claims
(typed n-ary relationships, temporal reasoning, provenance, contradiction handling), without changing the
meaning of their tasks. Nothing new was downloaded; facts below come from the original repositories and
dataset cards, checked today.

## Summary

| | CronQuestions | AVeriTeC | ComplexWebQuestions | LongMemEval (selected categories) |
|---|---|---|---|---|
| Source and licence | github.com/apoorvumang/CronKGQA, **MIT**; KG from Wikidata (CC0) | github.com/MichSchli/AVeriTeC, data on Hugging Face (chenxwh/AVeriTeC), **CC BY-NC 4.0** | tau-nlp.sites.tau.ac.il/compwebq (v1.1); **no licence stated** in the original repository | huggingface.co/datasets/xiaowu0162/longmemeval-cleaned, **MIT** (already downloaded) |
| Size | 410k questions over a Wikidata temporal KG (`data_v2.zip`, Google Drive) | train and dev claims (500 in dev) plus a 2,215-claim test set (claim JSON under 11 MB); dev knowledge store alone **11.5 GB** zipped | 34,689 questions with SPARQL over Freebase 2015 and web snippets | 500 questions; ~200k turns (S) |
| What it tests | Temporal QA over a given KG: simple time/entity, before/after, first/last, time joins | Claim verification against web evidence: Supported, Refuted, Not Enough Evidence, Conflicting/Cherry-picking | Compositional multi-hop questions (conjunction, superlatives, comparatives) | Memory from conversations; temporal reasoning, knowledge updates and abstention are three of its categories |
| Official protocol | Hits@1/10 per question type; **perfect entity linking assumed** | AVeriTeC score: verdict accuracy counted only when evidence (generated Q&A pairs) passes a METEOR-based threshold | Precision@1 against answer sets | LLM-judged answer accuracy; retrieval recall reported as a secondary analysis |
| Needs LLM? | No, if questions are parsed from the provided entity/time annotations and question type (an oracle for question understanding, which must be stated) | Yes: evidence questions, veracity and justification are generated; baseline searches the web | Yes for semantic parsing, or a Freebase instance (discontinued; dumps of hundreds of GB) | Yes for extraction from chat and for official answer scoring |
| Needs search / big data | KG load into TypeDB (millions of facts; a subset is feasible) | Web search or the 11.5 GB+ knowledge stores | Freebase or the provided snippets | No (have it) |
| Fit to GUPI's hypothesis | **High for temporal reasoning over structured knowledge**; low for knowledge formation (input is already a KG) | **High for the support/contradiction decision**; but the hard part is open-web retrieval and generation, not memory | Low: tests semantic parsing over a fixed KB, not memory formation, provenance or change | **Medium**: tests formation from raw conversation and knowledge updates, but on personal chat, where Phase 5 found structure does not help yet |
| Complexity / compute | Medium: KG subset loader, question-type router, temporal query functions; hours of ingestion for large subsets at ~150 facts/s | High: retrieval stack, NLI or LLM, licence restriction | High: KB hosting or LLM parsing | Low: adapters exist; real value needs LLM extraction |

## Recommendation: the two most useful

1. **CronQuestions**: it is the only candidate that directly tests temporal reasoning over typed, dated
   relationships, which is the part of GUPI most clearly tied to TypeDB. Offline evaluation is possible by
   loading a Wikidata subset as claims with validity intervals and routing questions by their annotated
   type and entities.
   *Limitations:* the input is a clean KG, so it says nothing about extracting knowledge from messy text;
   question understanding would be an oracle (annotated entities, times and type), which must be reported
   as such; answers are single entities or years, not provenance or contradiction; the KG is large, so
   only a documented subset is practical at current ingestion speed; its published model scores
   (embedding-based CronKGQA) are not comparable to an oracle-parsed symbolic system.
2. **LongMemEval, temporal-reasoning, knowledge-update and abstention categories**: already downloaded,
   MIT, with adapters, development/held-out split and first-run baselines from Phase 5. Knowledge updates
   and abstention are exactly the "changing and uncertain knowledge" behaviour the specialist direction
   is about, and it measures formation from raw text rather than a pre-built KG.
   *Limitations:* conversational, personal content (not complex organisational knowledge); without real
   LLM extraction the structured path has nothing to work with (Phase 5: no entity handle in 49 of 53
   development questions); the official metric is LLM-judged answer accuracy, so offline results stay
   retrieval-only.

**Not now:** AVeriTeC is the best fit for the "does the source support this claim" decision, but it needs
web-scale evidence or an 11.5 GB+ store, generated evidence and an NLI/LLM component, and it is
non-commercial. Worth revisiting once the formation engine has a real support-assessment provider; its
gold question-answer evidence could then be used as oracle evidence to test that decision alone.
ComplexWebQuestions is not recommended: it tests semantic parsing over a fixed knowledge base, its
licence is unstated, and it needs Freebase or an LLM parser.

**Neither recommended benchmark tests the specialist domain** (organisational knowledge with decisions,
obligations, conflicting reports and corrections). That is why a purpose-built dataset is proposed in
`domain-and-evaluation.md`, with the external benchmarks as independent checks.

## Graphiti as a baseline
github.com/getzep/graphiti, Apache-2.0, actively maintained. It needs an LLM for extraction (OpenAI by
default; Anthropic and OpenAI-compatible endpoints supported) and Neo4j, FalkorDB or Neptune as its store.
A fair comparison therefore needs an LLM budget or a local model server, and a second database for the
baseline (acceptable for a baseline, since GUPI itself would still use only TypeDB). Not practical under
the current offline, no-paid-API constraint; planned for when real extraction is approved.
