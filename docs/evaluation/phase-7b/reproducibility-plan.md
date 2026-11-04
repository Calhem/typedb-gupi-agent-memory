# Reproducibility plan

## The manifest
[manifest.draft.json](manifest.draft.json) lists every field to be frozen.
- **Its status is `draft`,** and it must stay a draft while the independent corpus is missing.
- **Fields still unknown** are `null`, with the reason.
- **Finalising:**
  - **The file:** it becomes `manifest.json`, with status `frozen`.
  - **When:** in Stage 2 step 6, after the corpus and gold are frozen and before the first scored model run.
- **Once frozen,** it is never edited. A later change needs a new manifest version, and the reason is
  recorded.

| Field | Content | Where it comes from |
|---|---|---|
| corpus | the S1, S2 and DEV files: SHA-256, row counts, the contributor codes per role | the files as received; hashed on receipt |
| gold | the assertions-A, assertions-B and adjudication files, and the adjudicated gold: SHA-256; agreement statistics | the annotation step |
| splits | S1 and S2 (scored), DEV (development only); the earlier development sets listed as development | corpus-specification.md |
| extractors | `rules:v2.1` (source hash); `model:candidate-v1` (source hash, prompt version, prompt and schema hash, model id, effort, thinking setting) | the code |
| contract | the `gupi.candidate/1` source hash; the validation source hash; C1 fix commit; D3 decision | the code |
| formation | the `formation:v1` source hash | the code |
| scorer | the scorer source hash; the thresholds file hash (success-criteria.md) | the code and docs |
| runtime | Python, typedb-driver and anthropic versions; TypeDB 3.14.1; hardware | the environment |
| cost limits | ledger lifetime limit; the per-run cap | the ledger |
| run order | the passage order (seeded); the stopping-rule parameters | the protocol |

## The procedure
1. **Receiving files:** contributor files arrive outside the developer's checkout. A custodian (the owner)
   hashes them and records the hashes in the draft manifest.
2. **Checking them:** the annotation checker is run (structure only). Problems go back to contributors, never
   fixed by the developer.
3. **The gold:** the adjudicated gold is frozen and hashed.
4. **The code:** the code is frozen at a tagged commit. Every source hash and the prompt hash are recorded.
   The manifest is finalised and committed.
5. **The scored runs:** they record every model request and response locally (git-ignored, kept by the
   owner), plus the ledger entries.
6. **Rescoring:** it is possible offline at any time from the recorded responses plus the frozen gold, and
   must give identical numbers.
7. **Publishing:** results are committed as first-run files and never overwritten. Contributor-authored
   passages are committed only if the contributors agree. Otherwise only ids, hashes and metrics are
   committed.

## What cannot be reproduced exactly
**Live model output:**
- **Why:** there is no seed control, aliases can change, and fallbacks can change the model.
- **How it is handled:** the recorded responses are the reproducible artefact. A live rerun is a separate,
  labelled run.
