# Compatibility and regression results (Stage 2B)

**Environment:** TypeDB 3.14.1 and Python 3.13 (with the `embeddings` extra).
- **Nothing external:** no API call, model inference or model download.
- **Spending:** $0.

## Format 1.0 stays valid and unchanged
| Check | Result | Where |
|---|---|---|
| 1.0 candidate ids are unchanged | the ids in the Phase 6D first-run world trace are reproduced exactly | `tests/unit/test_candidate_format_11.py` |
| 1.0 sets validate, and 1.1 fields in a 1.0 set are refused (`version`) | passes | the same file |
| a stored 1.0 payload reads back equal, still 1.0 and still valid | passes | `test_a_stored_1_0_payload_stays_readable` |
| `rules:v2` / `rules:v2.1` still emit 1.0; the default extractor is unchanged | yes | `test_a_legacy_1_0_claimant_without_a_kind_is_not_made_a_person` |
| recorded `gupi.model-response/1` fixtures are still read | all 26 developer responses (all format /1) are read by `model:candidate-v1.1`. Their vocabulary (`organization`, `unclassified`) maps to `organisation`, `unknown` | `test_format_1_1_output_and_both_response_formats`; the harness run |
| schema | **no migration**; no schema file changed | — |

## Regression runs, against the committed results
| Run | Compared with | Result |
|---|---|---|
| full test suite | — | see README.md (final count) |
| D1/D2 versions (`gupi.benchmarks.diagnosis.versions`: Phase 4, 6B, 6C/adversarial, world, samples, for `rules:v2` and `rules:v2.1`) | `extractor-d1-d2/comparison.json` | **0 differences** |
| 7A probes (`diagnosis.probes`) | `phase-7a/probes-first-run.json` | **0 differences** |
| 7A Path A / Path B (`diagnosis.pathcompare`) | `phase-7a/probe-results.json` | **0 differences** |
| Phase 6D, all parts, manifest v3 | `phase-6d/first-run` | **identical** apart from three scale timing fields (below) |

## Phase 6D against manifest v3
**The manifest:** [manifest-v3.json](../../phase-6d/manifest-v3.json), version 3.
- **What it keeps from version 2:** the same datasets, splits, gold and scoring.
- **Only four code hashes differ from version 2:**

| Manifest entry | File | Changed by |
|---|---|---|
| candidate IR | `src/gupi/formation/candidate.py` | format 1.1 (`fea49b6`) |
| validation | `src/gupi/formation/validate.py` | format 1.1 (`fea49b6`) |
| policy formation:v1 | `src/gupi/formation/form.py` | C2 (`e012f48`), D3 (`538e6c1`), F1 (`ec6e3f5`), inferred basis (`6d4cda2`) |
| candidate store (core/0012) | `src/gupi/formation/store.py` | D3 (`538e6c1`) |

**How the manifest was made:**
- **A regeneration:** v3 was first written at `fe95b6c`, then regenerated once (`92f3f70`) after the
  inferred-basis fix and before any run used it.
- **What was not touched:** manifests v1 and v2, `first-run/` and `current-v2/`.

**The run:** the normal runner, `--label current-v3 --parts all --manifest docs/evaluation/phase-6d/manifest-v3.json`.
- **The results:** [current-v3/](../../phase-6d/current-v3/) and its aggregate.md.
- **The comparison:** [current-v3-compare.json](../../phase-6d/current-v3-compare.json).

| Part | Identical to first-run |
|---|---|
| world (Phase 4 answers: 13 / 13 / 13 / 13 / 5 of 15; 0 unsupported definitive; 6/6 abstentions) | yes |
| Phase 2 held-out formation | yes |
| frozen 6B (30/30, 30/31; formed 20 / withheld 4 / review 6) | yes |
| adversarial (17/17 on every measure) | yes |
| LoCoMo held-out (8,380 retrieval rows) | yes |
| LongMemEval extraction and subset | yes |
| scale probe (930 candidates, 620 claims; resubmission writes nothing) | yes, except `extract_s_per_obs`, `ingest_s_per_obs`, `submit_s_per_obs` |

**The three differing fields are timings.** The comparison tool does not ignore them, a known gap that was
already present for current-v2. The latency columns in aggregate.md also differ, as expected.

**What C2, D3 and F1 changed here:** nothing that these results measure.
- **C2:** claimant kinds are not recorded in these results.
- **D3:** no input has a null-target correction.
- **F1:** no input has a copy of a forwarded copy.

## Developer-fixture harness (engineering check, not evidence)
**The run:** [dev-harness-run.json](dev-harness-run.json), on the same fixtures and hashes as Stage 2A.
`stage-2a/dev-harness-run.json` is untouched.

| System | Stage 2A | Stage 2B |
|---|---|---|
| `rules:v2.1` | precision 14/14, recall 14/24; formed 12, review 2; agrees 13/14 | precision 14/14, recall 14/24; formed 11, review 2, withheld 1; **agrees 14/14** |
| `model:candidate-v1` → `-v1.1` | precision 17/17, recall 17/24; formed 12, review 4, withheld 1; agrees 16/17 | precision 18/19, recall 18/24; formed 11, review 6, withheld 2; **agrees 18/18** |

**Severe errors:** 0 for both systems.
**`copies_formed`:** 0 for both systems.

**The passages that changed:**

| Passage | Stage 2A | Stage 2B | Why |
|---|---|---|---|
| DEV-108 (second forwarded copy) | formed | withheld (both systems) | F1 |
| DEV-105 (Halden Press, an organisational claimant, an allegation) | `claimant-kind-not-representable`, no candidate | matched, **review** (allegation) | C2 |
| DEV-126 (a retraction with no matchable target) | `correction-target-unresolved`, no candidate | a **partial** match, review, with a null target and flag `correction-target-unresolved` | D3 |

**DEV-126 in detail:** the recorded response paraphrases the predicate, so it is a partial match.
- **Where it goes:** it is listed for adjudication (1 item). It is not counted as matched.
- **Why precision moved:** that partial is the reason precision is 18/19, not 19/19.
