# Phase 7A: extraction pipeline diagnosis

Date: 2026-11-04. Branch `feature/phase-7a-extraction-diagnosis`, from `main` at `c58d3b1`. TypeDB 3.14.1.

**This is diagnosis only:**
- **Unchanged:** production extraction, validation, formation, answering, schemas and migrations.
- **Not done:** no paid API call, no model download, no new extractor.

**Measured and estimated results are labelled throughout.**

## Conclusion
**Why the result is zero:** `rules:v2` produced no candidates from LoCoMo or LongMemEval because of two
things together:
- what those conversations talk about (mostly outside employment and reporting)
- how they talk about it (when employment does come up, the employer is unnamed, and the phrasing is one the
  patterns do not cover)

**What it is not:** the pipeline is sound, and nothing was lost to validation or formation. Context
resolution is a real but secondary gap.

**One correctness defect was found on the way:**
- **The defect (D1):** capitalised pronouns are read as names, and become believed claims about a person
  called "She".
- **The gap (D2):** some in-domain sentences are dropped silently.

## Completion report
| # | Question | Answer | Kind |
|---|---|---|---|
| 1 | Branch head and tests | the head of `feature/phase-7a-extraction-diagnosis` (see the final report); the full suite passes against TypeDB 3.14.1 | measured |
| 2 | Is the zero reproduced? | **Yes, exactly,** independently of the 6D runner: 0 raw candidates from all 5,882 LoCoMo and 246,750 LongMemEval S turns, and from a 5% hashed subset (counts.json) | measured |
| 3 | Pipeline defects? | **None.** Text, speakers, ids, order, timestamps and the TypeDB round trip are intact. The extractor is called for every turn with no exceptions. The adapter path gives results identical to direct calls (pipeline-audit.md). Two extractor defects instead (D1, D2) | measured |
| 4 | Sample and domain coverage | 60 representative + 40 targeted turns (development splits). Representative: 28/60 turns hold potentially useful memory, 39 assertions, of which **1** is in the supported domain, 7 borderline and 31 outside it | estimated (one annotator) |
| 5 | Extraction success within the supported domain | Benchmark sample: **0 of 8** clear in-domain assertions extracted (0 of 25 including borderline). Probes: 15 of 48 that should extract did (11/11 supported phrasings, 4/37 variations); the brief's 10 sentences: 4 of 8 extracted, with correct temporal, attribution and certainty readings, plus 2 correctly left alone. Phase 2 held-out: 5/12 | measured |
| 6 | Distribution of failure causes | earliest stage, representative (39): outside the domain 31, unsupported phrasing 1, borderline 2-or-3 7; targeted (46): 29, 7, 10. Context (4–7) never the earliest, but needed by 24 of 85; validation and formation 0 (never reached) | estimated stages, measured extractor outputs |
| 7 | Dominant limitation | **domain, then language;** context third; integration none | — |
| 8 | Gain from expanded rules | **Small on conversations, large on organisational prose** (*estimates*): representative 0 → 1/39 with the same contract (8/39 if unnamed employers get a placeholder); Phase 2 held-out about 5/12 → 10/12 (upper bound) | estimated |
| 9 | Local model vs Claude | Both feasible, neither ready: the existing Claude extractor emits the old contract, not `gupi.candidate/1`. Claude: about $1–5 per 100 passages (Opus 5.5) or about $0.5–2.5 (Sonnet 5.5), needs an API key with credits (not the Max subscription). Local: 7–8B at 4-bit fits 16 GB at about 10–20 s per passage, but needs a runtime and a 4–6 GB download (extractor-options.md) | estimated |
| 10 | Recommended 7B | 40 fresh, independently authored organisational passages (primary) + 40 new conversational turns (secondary), annotated before running; `rules:v2` vs a Sonnet 5.5 `gupi.candidate/1` extractor (optionally a local model), scored deterministically for precision, recall, field fidelity, invention, cost and latency, capped at $3; decision thresholds fixed in advance (phase-7b-proposal.md) | proposal |

## Deliverables
| File | Contents |
|---|---|
| [pipeline-audit.md](pipeline-audit.md) | the traced path, every check, Path A vs Path B, the independent counts, defects D1 and D2 with proposed regression tests |
| [sample-manifest.json](sample-manifest.json) | dataset versions and hashes, splits, sampling rules, seeds, every sampled turn key with its text hash |
| [annotation-guidelines.md](annotation-guidelines.md) | the domain categories (A, A?, B, C) and the failure categories, as applied |
| [sample-results.csv](sample-results.csv) | one row per annotated fact (or per empty turn): category, stage, needs, extractor outcome; no dataset text |
| [probe-results.json](probe-results.json) | the brief's ten probes on Path A and Path B (LoCoMo and LongMemEval adapters), and six benchmark turns by id |
| [coverage-analysis.md](coverage-analysis.md) | domain, linguistic and contextual coverage, and the three ceilings with intervals and assumptions |
| [extractor-options.md](extractor-options.md) | rules vs local model vs Claude |
| [phase-7b-proposal.md](phase-7b-proposal.md) | the recommended experiment and its decision criteria |

**Supporting files:**
- **Sample:** [SAMPLING.md](SAMPLING.md) and [sample.json](sample.json), the frozen sample.
- **Annotations and classification:** [annotations.json](annotations.json), and
  [classification.json](classification.json), `rules:v2` on each sampled turn.
- **Audit and counts:** [audit.json](audit.json) and [counts.json](counts.json).
- **Probes:** [probes-first-run.json](probes-first-run.json), the 53 frozen probes of
  `tests/fixtures/diagnosis/probes-v1.json`.
- **Scripts:** in `gupi.benchmarks.diagnosis` (`sample`, `audit`, `classify`, `probes`, `pathcompare`,
  `counts`, `deliverables`).

## Order of work (each step committed before the next)
1. The sampling protocol and sample, frozen before any per-turn output was examined.
2. The pipeline audit, run on aggregates and on five turns chosen by hash. It holds no sampled text.
3. The fact-level annotations, committed before `rules:v2` ran on any sampled turn.
4. The classification run.
5. The probes: v1 and v2 were each committed before running, and their first runs were kept unchanged.
6. The independent counts.
7. This analysis.

## Limitations
- **One annotator,** the implementer, who also wrote `rules:v2`.
  - **What it affects:** the A, A? and B boundary, and "potentially useful", are judgements.
  - **What would remove it:** a second annotator.
- **Development splits only,** to keep held-out turns unread. Aggregates also cover the held-out splits, and
  agree.
- **Small samples:** the intervals are wide (coverage-analysis.md). The targeted sample is biased towards work
  talk by design and is reported separately.
- **Heuristic rejection reasons:** the breakdown in audit.json is an evaluation heuristic, not the
  extractor's reasoning.
- **Not measured:** the local-model and Claude figures are estimates; nothing was run.
- **A correction to the earlier interim report:**
  - **The wrong figures:** it said "4 of 39 variations" and "15 of 50".
  - **The correct figures:** 4 of 37 and 15 of 48, as above.
