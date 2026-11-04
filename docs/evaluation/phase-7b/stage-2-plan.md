# Stage 2 plan: implementation sequence and approval dependencies

Nothing here may start without the owner's approval. Each gate is approved separately.

## Approvals required
| # | Approval | Needed for | Cost |
|---|---|---|---|
| **G1** | Who writes S1 and S2, who annotates (two people) and who adjudicates; all other than the developer | everything after it | contributor time (estimate: authoring 4–6 h; each annotator 4–6 h; adjudication 2–3 h) |
| **G2** | Fix **C1** (schema-aware validation of `statement` attributes) on its own branch, test first | a fair statement score | none |
| **G3** | Decision **D3**: how an unresolved correction target is represented (see below) | corrections that must reach review | none |
| **G4** | Implement `model:candidate-v1` (code, prompt `p2`, recorder, offline tests) | building B | none (no calls) |
| **G5** | Spending for prompt development on DEV material only | B's development | up to **$1** |
| **G6** | Spending for the scored runs (B Sonnet 5.5; optional B′ Haiku 5.5), with an API key for an account with credits (not the Max subscription) | the measurements | up to **$2** (total Stage 2 ≤ **$3**, within the $10 lifetime ledger) |
| G7 | Optional: a local model (runtime install and 4–6 GB download) | arm C | disk and time |

**The authorised spend today is $0.** Until G5 and G6 are approved, no request is sent, test calls included.

## Decision D3 (unresolved correction targets)
**The problem:**
- **What fails:** a stated correction whose target cannot be resolved ("Sorry, I meant April") without the
  cue at the start of the passage would be formed without review.
- **Why:** `relations` require a resolvable target, and formation's correction cue only checks the start of
  the passage.

**The options:**
- **(a)** A contract amendment (`gupi.candidate/1.1`): a relation target `unresolved`, accepted by validation,
  which always routes to review.
- **(b)** Within `gupi.candidate/1`: a placeholder target `candidate:unresolved`. It is accepted today
  because of the `candidate:` prefix, and routes to review. It works, but it is a stand-in id.
- **(c)** A formation policy change: any candidate with `basis = inferred`, or with an extractor-reported
  correction cue, goes to review.

**The recommendation:** (a). It is explicit, and it is versioned.

## Sequence
1. G1, then: contributors produce S1, S2 and the gold. The developer prepares nothing for them beyond the
   templates.
2. G2 and G3: the contract fixes, each with tests, merged after review. The `rules:v2.1` baseline results
   are recomputed and labelled.
3. G4: implement `model:candidate-v1`, offline only:
   - **The pipeline:** grounding, normalisation, outcomes and recorder.
   - **The tests:** recorded and synthetic responses, including every failure outcome.
4. G5: develop the prompt on DEV material. The development spend is recorded in the ledger.
5. Freeze: prompt, schema, scorer, thresholds and manifest (reproducibility-plan.md).
6. G6: the scored runs, once each, under the stopping rule.
7. Residue adjudication, then the report, then a stop for review. Adoption is a separate decision.

## Risks to watch
- **Contributors are the critical path.** Without them the experiment does not proceed, and no synthetic
  substitute will be labelled independent.
- **Prompt overfitting to DEV:** keep DEV small, and different in style from S1.
- **Pricing or model changes** between design and execution: recheck them at G6.
