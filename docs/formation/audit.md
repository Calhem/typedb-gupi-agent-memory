# Phase 6A audit: what the Memory Formation Engine builds on

Date: 2026-11-03. Branch `feature/phase-6-memory-formation`, from main `8cbc29b`.

This audit reads the code as it is. Nothing in it has been changed.

## 1. Ingestion (`gupi.memory.Memory.ingest`, `gupi.records`)
- **One transaction per batch.** A `Batch` of sources, contexts, observations, referents, mentions and
  claims is all recorded, or none of it.
- **Ids come from content** (`gupi.ids`), so re-ingesting the same batch is a no-op.
- **Transaction time is never taken from callers.** `recorded-at` and `received-at` come from GUPI's clock.
- **A claim** has a type, role players (`roles`), at least one evidence span, a `ValidTime` (start and end
  windows), values, time precision, `valid-to-basis`, method, confidence, basis (explicit or inferred) and,
  since core/0010, polarity.
- **Gap: a claim has no field for**
  - who asserted it, other than the observation's author
  - how it reached the source (reported, forwarded)
  - its modality (planned, hypothetical)
  - the source's own hedging
  - a correction it makes

## 2. Extraction (`gupi.extraction`)
- **The contract** (`contract.py`). An extractor returns JSON for one observation. The validator trusts
  nothing:
  - mentions and quotes must match the text
  - types, roles, player kinds and attributes must exist in the schema
  - time phrases must appear in the text, and are read by `gupi.timeexpr` (never dates from the extractor)

  Failures are rejected with reasons. A generic `statement` with a known predicate becomes a typed claim.
- **The pipeline** (`pipeline.py`).
  - There is one `extraction-run` per (extractor, prompt version, observation). It records a run report:
    rejections, notes, and how each time phrase was read.
  - Re-runs are skipped.
  - **Validated claims are ingested straight into memory as hypotheses** (no review). So today the only
    separation between "extracted" and "accepted" is review status.
- **The rule extractor** (`rules.py`, offline default). It has eight sentence patterns, one clause per
  sentence, and no negation or pronoun handling.
- **The Claude extractor** (`claude.py`). It follows the same contract, behind the fail-closed budget ledger.
  It has never been run live.

## 3. Defects and gaps found
| # | Finding | Evidence |
|---|---|---|
| A1 | **"Since" becomes an exact start.** "Since March 2025, Nora Vance works at Halden as CTO" and "Nora Vance joined Halden as CTO in March 2025" both become a start window of 1 March to 1 April 2025. "Has reported to X since June" does the same. The difference between lower-bound evidence of continuity and a stated start is lost at extraction. | rule patterns `has reported to ... since`, `LEADING_TIME`; contract `_time` maps any `start` phrase to both start bounds. Reproduced on 2026-11-03. Known issue in docs/known-issues.md. |
| A2 | **Corrections are dropped.** The prefix in "Correction: Nora Vance left Halden in May 2025" is stripped (`PREFIX`), and nothing records that the sentence corrects an earlier claim. Supersessions exist (ADR 0006), but only a reviewer can create one. | rules.py `PREFIX`; there is no correction field in the contract |
| A3 | **No negation in extraction.** The schema can store negations since core/0010, but neither extractor nor the contract can express one. | rules.py docstring; the contract has no polarity |
| A4 | **Attribution collapses to the observation.** "Joaquín told me he is leaving" is attributed to the message's author. There is no "asserted by", "via" or transmission. | records.Claim; contract |
| A5 | **No modality or hedging.** Plans ("will join in May"), hypotheticals and "probably" become ordinary claims, or are missed. | contract; rules |
| A6 | **Extraction writes straight into memory.** There is no candidate stage that a formation policy (salience, support, acceptance) could act on before claims exist. | pipeline.extract → memory.ingest |
| A7 | **The time reading is in the run report but not on the claim.** The phrase, explicit or inferred, and the assumption are recorded per run (`Extraction.times`), but the claim keeps only bounds and precision. | contract `_time`, `Extraction.report` |

## 4. Interfaces the engine must feed
- **Proposition keys:** `proposition_key(type, roles)`, a hash of the type plus its role players.
  - Values, polarity and time are deliberately excluded, so all claims about one proposition can be found
    together, positive or negative.
  - Candidates must produce the same key as the claim they become.
- **Provenance:**
  - observation (verbatim content, content hash, observed-at, context, author)
  - source
  - `evidence` spans on each claim
  - `extraction-run` and `extraction-output`, which link outputs to the run
- **Review:**
  - `review.queue` lists hypotheses, oldest first, with conflicts and alternatives
  - `Memory.review` and `review_many` record verdicts as historical events
  - `Memory.supersede` records corrections
- **Answer semantics:** v1 (default) and v2 (`semantics="v2"`, ADR 0009) both read a claim's `ValidTime`
  and, for v2, its `polarity`.
  - **v2 can already express lower-bound continuity.** A claim with no earliest start and a latest start of
    1 April ("held at least since March") has a start window that is open below. v2 treats instants inside it
    as UNKNOWN, and instants from 1 April until the observation as directly true.
  - So the remedy for A1 needs no change to answer semantics, only a correct mapping from the phrase.
- **Budget ledger** (`gupi.budget`, database `gupi-ledger`): fail-closed reservations for paid calls.
  Untouched by 6A.

## 5. Consequences for 6A
- A **separate, versioned candidate representation** (candidate-ir.md) sits between an extractor's output
  and memory. It keeps what A1-A5 and A7 lose. It is validated on its own, and it never becomes a claim in
  6A.
- **Existing behaviour is unchanged:** ingestion, the extractors, v1 and v2, the benchmarks and the ledger.
