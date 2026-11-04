# Phase 6D reproducibility after Phase 7B Stage 2A (2026-11-04)

**What happened:**
- **The trigger:** Stage 2A's C1 and D3 corrections changed three source files that the original Phase 6D
  manifest records.
- **The runner's response:** it then refused to run against the current tree. That refusal is correct, and it
  is kept.
- **What is untouched:** `manifest.json` (version 1) and `first-run/` are unchanged.

There are two separate claims, checked separately.

## 1. Historical reproducibility, at the original commit
- **How:**
  - **The checkout:** a detached checkout of `c58d3b1` (main when Phase 6D was merged).
  - **The environment:** the same environment as the original run (Python 3.13.17, the `embeddings` extra;
    the same dataset files and local embedding model).
  - **The run:** the unmodified runner, checked against the original manifest (which matched), `--parts all`.
- **Result** ([historical-reproduction-compare.json](historical-reproduction-compare.json)):
  - **Identical to `first-run` in every part:**
    - the world (Phase 4 answers)
    - Phase 2, frozen 6B, adversarial
    - LoCoMo held-out
    - LongMemEval extraction and subset
  - **The scale probe** differs only in three per-observation timing fields: `extract_s_per_obs`,
    `ingest_s_per_obs` and `submit_s_per_obs`.
  - **Why those fields differ:** the comparison tool ignores other timings, but not these names. That is a
    known gap in the tool, recorded in remaining-limitations.md. The tool is left unchanged, because
    manifest version 2 records its hash.
- **The outputs** of that run stayed in the temporary checkout. Only the comparison is committed.
- **One false start:**
  - **What happened:** a first attempt ran in a freshly created environment, on Python 3.15 without the
    embeddings extra, and its world and LoCoMo parts failed.
  - **What was done:** it was stopped and discarded, and rerun in the matching environment.

## 2. The frozen inputs against the current implementation
**How:**
- **The new manifest:** [manifest-v2.json](manifest-v2.json), version 2, generated from `cff9261`.
- **What it keeps from version 1:** the same datasets, splits and scoring rules.
- **What it adds:**
  - the current hashes of the three changed files
  - supplementary hashes for code version 1 did not track
- **The run:** the normal runner with `--manifest docs/evaluation/phase-6d/manifest-v2.json --parts all`, at
  `168c59b`.
- **The results:** [current-v2/](current-v2/), with [aggregate.md](current-v2/aggregate.md).

**Result** ([current-v2-compare.json](current-v2-compare.json)):
- **Identical to the first run** in every part except the same three scale timing fields.

| Metric | first-run | current-v2 |
|---|---|---|
| world: GUPI end to end / no reviewer / on gold claims / Phase 4 pipeline / keyword | 13 / 13 / 13 / 13 / 5 of 15 | the same |
| world: unsupported definitive (end to end) | 0 | 0 |
| world: abstained when it should (end to end) | 6/6 | 6/6 |
| world: candidates stored, decisions, formed, reviewer actions | 11, 11, 11, 1 | the same |
| Phase 2 held-out formation: recall, precision, outcomes | 5/12, 5/5, formed 5 | the same |
| frozen 6B: precision, recall, fields; outcomes formed / withheld / review | 30/30, 30/31; 20 / 4 / 6 | the same |
| adversarial (17 development cases), every measure | 17/17, 0 unsupported definitive | the same |
| LoCoMo held-out: candidates; retrieval rows | 0; 8,380 identical | the same |
| LongMemEval: candidates (extraction); subset retrieval rows | 0; 254 | the same |
| scale probe: candidates, claims, pending, resubmission | 930, 620, 186, writes nothing | the same |

**The effect of stricter schema-aware validation (C1) here: none.**
- **Why:** every candidate these inputs produce was already schema-valid, and they contain no generic
  statements.
- **What did not change:** no candidate was newly refused, and no formation or review decision changed.

**The effect of D3 here: none.** No correction in these inputs had several plausible targets, or a
superseded target.

## The source hashes that changed (version 1 to version 2)
| Manifest entry | File | Version 1 | Current | Changed by |
|---|---|---|---|---|
| validation | `src/gupi/formation/validate.py` | `9a3a5c909f44…` | `5cf574da8ca2…` | C1 (`6ace7df`) |
| policy formation:v1 | `src/gupi/formation/form.py` | `236a73e4ec73…` | `17b5bd0b5fe8…` | C1 (`6ace7df`), D3 (`9c3815f`) |
| candidate store (core/0012) | `src/gupi/formation/store.py` | `d4ad0b76a250…` | `6f20582731ea…` | C1 (`6ace7df`) |

**What did not change:**
- **The other tracked sources:** all 13 others are unchanged. These include rules:v2, the candidate IR,
  answer semantics v2, query, qualification, the evidence retrievers, the Phase 4 scorer, rules:v1, the time
  expressions, the 6B and 6C scorers, and the benchmark config and split.
- **The inputs:** dataset files, fixtures and gold answers are unchanged (their hashes are equal), as are the
  splits, the scoring rules, the schema and migrations.
- **The offline harness:** it touches none of the tracked files.

**A file version 1 never tracked:**
- **What changed:** `src/gupi/extraction/contract.py` (`SchemaInfo`) also changed in C1, but version 1 does not
  record it.
- **What version 2 does:** it tracks this file, the extractor registry and the runner's own modules, under
  `supplementary_code`.

**Rerunning either:**

    uv run python -I -m gupi.benchmarks.e2e --label <new> --parts all                                      # checks version 1: refuses on the current tree
    uv run python -I -m gupi.benchmarks.e2e --label <new> --parts all --manifest docs/evaluation/phase-6d/manifest-v2.json
