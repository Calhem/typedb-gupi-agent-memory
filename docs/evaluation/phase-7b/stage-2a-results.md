# Phase 7B Stage 2A results: contract correctness and offline evaluation

Date: 2026-11-04.
- **Stage 1:** merged into main as `ff5d344` (non-fast-forward, of `0d3ca00` and `a77e1a9`).
- **Stage 2A branch:** `feature/phase-7b-offline-harness`, from `ff5d344`. Not merged.
- **Environment:** TypeDB 3.14.1.
- **Nothing external:** no API call, no model inference, no model download.

**Spending:** $0. The ledger database has never been created, so no API call has ever been made.

## What was done
| Objective | Result | Detail |
|---|---|---|
| C1 schema-aware validation | **fixed**: one admissibility rule for validation, the store and `form()`; statements validate; misplaced values and malformed statements are refused | contract-corrections.md |
| D3 correction targets | **enforced** for every case the contract can express: corrections always reviewed, nothing changed automatically; suggestions never resolve to a guessed or no-longer-believed target. The unresolvable, cue-less case needs a contract extension, which is **stopped for approval** | contract-corrections.md |
| Organisational claimants | **diagnosed**: a candidate-contract limitation plus a persistence-mapping defect; the schema is fine. The fix needs a contract extension, which is **stopped for approval**. The four claimant cases are defined by tests | contract-corrections.md |
| Offline `model:candidate-v1` | **built**: a strict response format; code-computed grounding, offsets, times and forwarding; explicit outcomes; no model connected | offline-extractor-interface.md |
| Developer fixtures | 26 passages, 24 hand-checked gold assertions, 26 recorded responses (10 deliberately faulty), all labelled developer-authored | development-fixtures.md |
| Offline harness | built and tested; runs without network; formation optional (local TypeDB) | offline-harness.md |

## Tests
| Point | Result |
|---|---|
| start (main `0d3ca00`) | 412 passed, 19 expected failures |
| Stage 1 merged (`ff5d344`) | 412 passed, 19 expected failures |
| end of Stage 2A | 463 passed, 20 expected failures (see the final report for the head) |

**What changed in the expected failures:**
- **Retired:** the C1 demonstration, since C1 is fixed.
- **Added:** the two C2 claimant cases, pending approval.
- **Unchanged:** the 18 `rules:v2` D1/D2 demonstrations.

**New tests:**
- C1: 10
- D3: 7
- claimant kinds: 5 (2 of them expected failures)
- the interface: 23 unit and 2 integration
- the harness: 5 unit and 1 integration

## Before and after
- **The details:** contract-corrections.md has them for C1 and D3.
- **The original failures:** saved in `stage-2a/c1-original-failures.txt` and `d3-original-failures.txt`.
- **Behaviour that changed on purpose:**
  - **C1:** schema-invalid candidates are now refused at `store.submit`, and statements validate.
  - **D3:** two suggestion cases (several plausible targets; a superseded target).
- **Everything else is unchanged:** every historical result reproduces (contract-corrections.md, under
  historical compatibility).

## Developer-fixture harness run (engineering check, not evidence)
**On `rules:v2.1`:** precision 14/14, recall 14/24, 0 severe errors.

**On the recorded `model:candidate-v1` responses:** precision 17/17, recall 17/24, 0 severe errors.
- **The deliberate faults:** all 10 were stopped or downgraded before formation.
- **Finding F1:** the one admission disagreement is a formation gap, recorded in remaining-limitations.md.

The raw result is in `stage-2a/dev-harness-run.json`.

## Reproduction
    uv run pytest -q                                        # needs docker compose up -d (TypeDB 3.14.1)
    uv run python -I -m gupi.benchmarks.phase7b.harness tests/fixtures/phase7b-dev/offline \
        --responses tests/fixtures/phase7b-dev/offline/responses.json --formation --json /tmp/run.json
    uv run python -I -m gupi.benchmarks.diagnosis.versions --json /tmp/versions.json   # historical comparison

## Not done (out of scope, or needing approval)
- **Live work:** no live model integration, prompt or API call.
- **No independent corpus collection.**
- **No contract extension** for C2 or the D3 null target, and **no formation policy change** for the inferred
  basis.
- **No default-extractor change,** and nothing touched on the specialist branch.
