# Phase 7A diagnostic sample: protocol (frozen before any per-turn extractor output was examined)

`sample.json` is produced by `python -m gupi.benchmarks.diagnosis.sample --write`. The same command without
`--write` checks that it is reproduced exactly. It holds dataset ids, strata, lengths and SHA-256 hashes of
each turn's text, **never the text**: LoCoMo is CC BY-NC 4.0, and both datasets contain personal-seeming
content.

## Sources
| Dataset | File | SHA-256 | Split used |
|---|---|---|---|
| LoCoMo | `.data/locomo/locomo10.json` (commit `cbfbc1d…`) | `79fa87e9…98ff4` | development: conv-26, conv-30 (788 turns) |
| LongMemEval S cleaned | `.data/longmemeval/longmemeval_s_cleaned.json` (revision `98d7416…`) | `d6f21ea9…a3c442` | development: the 53 questions with sha256(id) mod 10 == 0; 26,572 distinct turns |

**Why only the development splits:**
- **They protect the held-out data:** reading turns in detail exposes them, so the held-out splits stay
  unread for any future extractor evaluation.
- **The aggregate findings carry over:** the zero-candidate result in Phase 6D held on development turns
  too (6D feasibility slice: LoCoMo dev, 0 of 788).

**Turn text** is exactly what the adapters give `rules:v2`:
- **LoCoMo:** the turn text, plus the shared-image caption.
- **LongMemEval:** the turn content.

## Rules
- **Ranking:** turns are ordered by `sha256("phase7a-sample-v1|<dataset>|<turn key>")`, lowest first.
- **Turn keys:**
  - **LoCoMo:** `<sample id>:<dialogue id>`.
  - **LongMemEval:** `<context id>:<position>`, where the context id is the session id plus a content hash,
    as in `gupi.benchmarks.longmemeval`.
- **Representative sample:** 30 turns per dataset.
  - **Length terciles:** computed over all eligible turns, in characters. The cut points are LoCoMo 92 and
    174, and LongMemEval 222 and 1,245.
  - **LoCoMo:** 2 conversations × 3 length terciles × 5 turns.
  - **LongMemEval:** 2 roles (user, assistant) × 3 terciles × 5 turns.
- **Targeted diagnostic sample:** 20 turns per dataset.
  - **Which turns:** those whose text matches a work-vocabulary pattern, fixed in `sample.py` (`WORK`)
    before any output was seen, and not already in the representative sample.
  - **How many matched:** 95 LoCoMo turns and 6,459 LongMemEval turns.
  - **How it is reported:** separately, never mixed into the representative figures.

**What the strata cover:**
- **They spread the sample over:** message length, speaker or role, and conversation.
- **They do not target:** fact type, pronouns, corrections, questions and so on. Those are recorded in the
  annotation, not selected for, so the sample is not biased towards turns likely to succeed.
- **The targeted sample** exists because the representative one is expected to contain few in-domain
  (employment and reporting) statements.

**Not changed after observation:** the sample file is write-once (`--write` refuses to overwrite it).
