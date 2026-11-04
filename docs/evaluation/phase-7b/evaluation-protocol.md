# Evaluation protocol

## Questions
| # | Question | Answered by | Kind |
|---|---|---|---|
| Q1 | Does model-assisted extraction find more relevant facts than `rules:v2.1` in unfamiliar specialist documents? | S1 recall and precision, A vs B (scoring-specification.md) | measured |
| Q2 | Does it preserve who asserted it, what it concerns, how it reached the source, how certain it is, whether it is denied, when it applies, and whether it corrects earlier information? | the field-fidelity metrics on matched pairs | measured |
| Q3 | How often does it invent an entity, relationship, date, attribution or certainty? | unsupported-claim and severe-error rates | measured (human-adjudicated residue) |
| Q4 | Can its output pass GUPI's existing validation and formation without weakening them? | schema-aware validation pass rate; formation outcomes against gold `expected_admission`; unsafe formations | measured |
| Q5 | Latency, compute, cost | ledger actuals, timings | measured in Stage 2; estimated now (model-options.md) |

## Design
- **Systems:**
  - **A:** `rules:v2.1`, unchanged.
  - **B:** `model:candidate-v1` with Sonnet 5.5.
  - **B′ (optional):** the same, with Haiku 5.5.
  - **C:** a local model, only if separately approved (model-options.md).
- **Same input:** every system gets the same observations (same text, author, document date and thread
  order), through the same ingestion code.
- **Same contract:** every candidate goes through `gupi.formation.validate` with the live schema, then
  `store.submit` (formation:v1) in a disposable database per system and set.
- **Extraction and formation measured apart:** extraction accuracy uses candidates; formation outcomes
  come from the store's decision records.
- **Two sets:**
  - **S1:** specialist passages, about 40, which decides.
  - **S2:** conversational turns, about 40, a secondary set.
  - **Reporting:** each set is reported separately, never pooled.
- **No tuning on S1 or S2:**
  - **Where the prompt is developed:** only on DEV material (developer-authored, labelled) and on earlier
    development sets.
  - **What happens before S1 and S2 are opened:** the prompt, schema, scorer and thresholds are all frozen.
- **One scored run per system.** It is reported unchanged, failures included. Any later run is labelled
  separately, and needs a fresh frozen corpus if anything was changed.

## Order of work (Stage 2; each gate needs approval)
1. **Contributors:** independent contributors write S1 and S2 (corpus-specification.md). The developer does
   not read them.
2. **Annotation:** two annotators annotate them, and an adjudicator resolves disagreements
   (annotation-guidelines.md). Agreement is reported.
3. **Freezing the corpus and gold:** the corpus, gold and adjudication are frozen and hashed
   (reproducibility-plan.md).
4. **Contract:** C1 and decision D3 are resolved, each with its own tests (stage-2-plan.md).
5. **Building on DEV only:** `model:candidate-v1` is implemented and tested offline (recorded and synthetic
   responses); its prompt is developed on DEV material only.
6. **Freezing the run:** prompt, schema, scorer, policy and thresholds are frozen. The manifest is
   finalised.
7. **Scored runs:** the scored runs (A, B, and B′ if approved), each once, under the stopping rule.
8. **Adjudication:** human adjudication of the unmatched residue (blind to which system produced it, where
   feasible).
9. **The report:** verdict against success-criteria.md.

## Blinding
- **Authors and annotators** never see extractor outputs or prompts.
- **The residue adjudicator** sees unmatched candidates with the system label removed. A and B candidates are
  shuffled together.
- **The developer** does not read S1 or S2 before step 6. Those files are kept outside the developer's
  working tree until then, and hashed on receipt.

## What this experiment does not establish
- **Other domains and model versions:** it shows nothing about performance on other domains, or on future
  model versions.
- **Conversation benchmarks:** S2 is small and secondary, so it does not measure LoCoMo or LongMemEval
  performance.
- **TypeDB:** it says nothing about the value of TypeDB itself. All systems use the same store.
