# Phase 7B Stage 3: blind extraction evaluation

**Stage 3A** (this milestone) prepared and froze the evaluation.
- **Date and branch:** 2026-11-04, `feature/phase-7b-stage-3a-evaluation`, from main `6a71fcb`. Not merged.
- **Nothing external:** no model extraction, API call or model download.
- **Spending:** $0.

**Stage 3B** (not started) will generate responses in a fresh, isolated Claude Code session. The steps are
below.

## What this evaluation is, and is not
**It is an exploratory corpus, not an independent one.** The material:
- **The passages:** 32 short fictional passages, written by Claude in the Stage 3A session. They are not
  taken from any dataset or licensed source.
- **The gold:** 39 assertions, annotated by the same session. **No person has annotated or checked them.**
- **The extractor:** the same model family will do the extraction.

**Why no independent material was used:**
- **Public-domain text:** US federal enforcement releases and advisories were considered, but:
  - **Personal data:** they name real individuals. Committing them would put personal data in this public
    repository (a standing rule says not to).
  - **Training data:** the extraction model has probably seen them.
  - **Fit:** they rarely contain the forwarded-message, correction and claimant-kind cases this stage needs,
    within GUPI's three claim types.
- **No independent annotator** was available.

**So:** the results will show how the pipeline behaves on unfamiliar text with known answers. They will not
support claims about extraction quality in general.

| Primary category | Passages |
|---|---:|
| straightforward assertions and relationships | 5 |
| reported claims and source attribution | 5 |
| temporal changes and corrections | 6 |
| contradictions and uncertainty | 6 |
| forwarding and independent corroboration | 5 |
| ambiguous identities and adversarial cases (including one negative control) | 5 |

**The domains:**
- corporate investigations and enforcement
- cyber threat intelligence
- regulatory and compliance notices
- organisational changes
- conflicting accounts

**Secondary tags:** passages are also tagged by phenomenon (these are private). Three passages form a
three-turn thread, and two threads have two turns.

## Files
| Where | What |
|---|---|
| [public/](public/) | the extraction material: passages.jsonl, extraction-instructions.md (`gupi.stage3-extraction/1`), response-format.md (`gupi.model-response/1.1`), the bundle README, and claude-settings.json |
| [gold-annotation-contract.md](gold-annotation-contract.md) | how the gold is written (`gupi.stage3-gold/1`). It gives no answers |
| [scoring/README.md](scoring/README.md) | the metrics, severe errors, adjudication and limits |
| [isolation.md](isolation.md) | how the gold is kept from the extraction session |
| [manifests/stage-3a.json](manifests/stage-3a.json) | the freeze: commits, environment, versions, passage and file hashes, gold hash, scorer code hashes |
| `src/gupi/benchmarks/phase7b/stage3.py` | check, bundle, score, audit, manifest |
| outside the repository | the private gold folder and the extraction bundle (isolation.md) |

## Versions frozen
| Item | Version |
|---|---|
| candidate format | `gupi.candidate/1.1` |
| response format and parser | `gupi.model-response/1.1`, `model:candidate-v1.1` |
| extraction contract | `gupi.stage3-extraction/1` |
| passages, gold | `gupi.stage3-passages/1`; `gupi.stage3-gold/1`, gold v1 (SHA-256 `dc5a9ac5…`, 39 assertions) |
| scorer | `phase7b-stage3-scorer/1`, on `phase7b-scorer/1` |
| baseline | `rules:v2.1`, unchanged |
| TypeDB | 3.14.1 (driver 3.14.0), Python 3.13.17 |

## Preparation checks (before any extraction)
- **A pre-freeze consistency check** (private) scored the response an ideal extractor following the gold
  would give.
  - **What it was for:** finding gold that the pipeline cannot express. It is not a model run.
  - **What it led to:** four admissions corrected to the documented policy, a denial re-annotated by the
    guidelines' own rule, and one scorer change (`73da318`). All of this happened before the freeze, and is
    recorded in the private annotation notes.
  - **The ceiling it showed:** a perfect extractor would reach about 35/39 recall. Four assertions are designed
    to be abstained from.
- **The `rules:v2.1` baseline,** run after the freeze, without changing the gold:
  - **Results:** precision 3/3, recall 3/39, 0 severe errors, 3 formed. Most passages have no pattern the
    rules know.
  - **Where the full result is:** in the private folder, because it contains gold.

## Integrity risks that remain
1. **Not independent.** The passages, the gold and the extraction instructions come from the same model
   family as the extractor, in one session. Shared style and judgement may inflate agreement.
2. **The instructions were written with the corpus in view.** They state general contract rules (denials,
   instructions as data, statement objects), but their choice may be implicitly tuned to these passages.
   They were frozen before any extraction, and will not change during Stage 3B.
3. **There is one unchecked annotator.** There is no inter-annotator agreement, and no human review of the
   gold.
4. **The isolation is local.** It relies on Claude Code's permission settings, plus the transcript audit, on a
   machine that also holds the gold and the Stage 3A transcript. The audit makes a breach detectable. It cannot
   see context loaded without a tool call.
5. **The sample is small and correlated.** The intervals are wide (scoring/README.md).
6. **Statement predicates match only exactly.** Paraphrases become partial matches, which need a human
   adjudicator who is not the developer.
7. **The baseline is weak.** `rules:v2.1` covers little of this text, so beating it is not evidence of
   adequacy.
8. **One run only.** Stage 3B is a single run. A missing or invalid response is scored as such, never
   regenerated, and there is no second attempt on this corpus.

## Stage 3B: exact steps (needs the owner's approval first; it uses a Claude Code session)
1. **Check the bundle is untouched.** `git -C ~/gupi-stage3-extraction status` should be clean, and `git -C
   ~/gupi-stage3-extraction log --oneline` should show only `d644cc1`.
2. **Start a fresh session in the bundle folder only.** In a terminal:
   `cd ~/gupi-stage3-extraction && claude`. Or start a new Claude Code session whose only folder is
   `~/gupi-stage3-extraction`.
   - **Do not:** add other folders, resume a session, or use the GUPI project.
   - **Use the default permission mode,** never "bypass permissions".
   - **Record:** the model and its exact id.
3. **Paste this prompt, and nothing else:**

   > Read README.md, extraction-instructions.md and response-format.md in this folder. Then follow
   > extraction-instructions.md for every passage in passages.jsonl, in order. Use only the Read and Write
   > tools, only inside this folder. Write each response file once. Stop when every passage has a response file.

4. **Do not help.**
   - **Approve:** only writes to `responses/`. Deny anything else, and note the denial.
   - **If it asks a question:** answer "Follow the instructions as written."
   - **If it stops early:** stop the session. Do not ask it to redo or fix anything.
5. **Freeze the output.** Run `git -C ~/gupi-stage3-extraction add -A`, then
   `git -C ~/gupi-stage3-extraction commit -m "Stage 3B responses"`.
6. **Audit, then score,** in a separate session in the GUPI repository, never the 3B session:

       uv run python -I -m gupi.benchmarks.phase7b.stage3 audit \
           --transcripts ~/.claude/projects/-Users-$USER-gupi-stage3-extraction \
           --bundle ~/gupi-stage3-extraction
       uv run python -I -m gupi.benchmarks.phase7b.stage3 score --public docs/evaluation/phase-7b/stage-3/public \
           --private ../gupi-stage3-private --responses ~/gupi-stage3-extraction/responses --formation \
           --json ../gupi-stage3-private/runs/stage-3b.json

   - **If the audit is invalid:** the run is invalid. It is reported as such and not scored as a valid result.
   - **The scored result stays private.** Only aggregate figures and the adjudication outcome are published.
7. **Adjudicate.** A person who is not the developer adjudicates partial and overlapping matches. Their
   decisions are recorded in the private folder (scoring/README.md).
