# Proposal: Phase 7B extraction experiment (not executed; needs approval)

## The question
**Does model-assisted extraction recover materially more of what people actually say, at the fidelity
GUPI's candidate contract demands, than the rules do?** The contract demands exact spans, time kinds,
attribution, modality, polarity and corrections. The rules are `rules:v2`.

**What 7A rules out as the main lever:** the adapter (no defect), and formation (never reached). The
extractor is what decides the result.

**What 7B will not answer:** whether a wider ontology is worth building. 7A shows that most conversational
memory is outside the domain. 7B keeps the current contract, so it measures the language gap, not the
domain gap.

## The smallest design that can answer it
### Material
**Two sets, frozen and annotated before any system runs:**

| Set | Contents | Author | Gold annotator | Role |
|---|---|---|---|---|
| **S1** fresh organisational passages | 40 short messages (chat, email, minutes) about employment and reporting, written freely: synonyms, first person, pronouns with antecedents, hedges, reported speech, corrections, plans, negations, dates in varied forms, and some passages with nothing in the domain | someone other than the implementer (the owner or a colleague), given only the domain description, not the patterns | a second person, using the 6B expectation format; disagreements adjudicated and recorded | **primary**: the language gap on fresh text |
| **S2** conversational turns | 40 development turns from LoCoMo and LongMemEval, newly drawn by a seeded rule that excludes the 7A sample and is weighted to work talk as in the 7A targeted sample | (the dataset) | as for S1 | **secondary**: whether anything changes on real chat (expected: little, because of unnamed employers) |

**Not used as evidence of generalisation:** the 6B and 6C sets, the 7A probes and the Phase 2
conversations. They may be run, but only as labelled development checks.

**Size:**
- **What 40 passages give:** about 50–70 gold candidates in S1.
- **What that can detect:** at that size a recall difference of about 25 points is outside the 95%
  intervals. Smaller effects would not be credible, and the report will say so.

### Systems (same input, same contract)
1. **`rules:v2`, as it stands:** the baseline.
2. **A model-backed `gupi.candidate/1` extractor:**
   - **Model:** Claude Sonnet 5.5 (`claude-sonnet-5-5`), a new prompt version emitting the candidate IR.
     Spans are found locally by exact substring search; the model's offsets are never trusted.
   - **Time:** time phrases are copied, then read by `gupi.timeexpr`.
   - **Effort:** low, to keep thinking short.
   - **Why Sonnet:** Opus 5.5 costs about twice as much for an extraction task; Haiku 5.5 is the fallback
     if the budget is tight.
3. **Optional, only if approved:** one local 7–8B model through llama.cpp, using the same prompt and
   constrained JSON. If there is no approval, it is skipped, not substituted.

**Option A** (`rules:v2.1`, including the D1 and D2 fixes) is a separate, cheap change. If approved first,
it can be run as a fourth system. The 7B comparison must not wait for it.

### Measures (scored deterministically; no LLM judge)
| Measure | Definition |
|---|---|
| precision, recall | the frozen 6B matching (type, role surfaces, polarity), reported separately with counts, per set |
| field fidelity on matched candidates | time kinds and windows, modality, commitment, attribution mode and asserted-by, relations (corrects, repeats) |
| invented or unsupported | candidates whose participant surface or time phrase is not in the passage (validator rejections), **plus** matched-type candidates that assert something the gold marks as unsupported (presupposition read as fact, resolved pronoun to the wrong person, a date not stated). Reported as a rate per passage and per candidate |
| formation outcomes | `store.submit` decisions (formed, withheld, review, rejected) for each system's candidates; nothing is formed without the policy |
| latency, cost | seconds per passage; dollars from the ledger (settled actuals), tokens in and out |

### Execution and safeguards
1. Freeze S1 and S2 with their gold and hashes, plus the scoring script, before any model call.
2. **One run per system, reported unchanged.** Defects are documented, not fixed and rerun.
3. **Model output enters only as candidates in a disposable database.** It never becomes accepted memory
   outside the formation policy, and never touches the main database.
4. **Budget:**
   - **Run cap:** `run_cap_usd=3` on the ledger.
   - *Estimate:* 80 passages × about $0.01–0.025 on Sonnet 5.5 comes to about $0.8–2.
   - **The ledger** refuses anything beyond the cap and the $10 lifetime limit.
5. **No retrieval or answering experiments.** Extraction only.

### Decision criteria (fixed in advance)
**Model-assisted extraction "materially improves GUPI" if, on S1:**
- **Recall:** at least 0.25 above `rules:v2`, with non-overlapping 95% intervals.
- **Precision:** at least 0.90.
- **Invented or unsupported candidates:** at most 5% of its candidates, and none formed without review.
- **Time-kind fidelity:** at least 0.90 of matched candidates. Attribution and commitment at least 0.85.
- **Cost:** under $0.05 per passage. **Latency:** under 30 s per passage.

**Outcomes:**
- **If it improves on recall but fails on fidelity or invention:** keep rules as the default, and use the
  model only to propose candidates for review.
- **If it fails on recall:** invest in rules (Option A), and revisit the ontology question instead.
- **On S2:** reported, but not part of the decision. A large S2 gain would be a reason to revisit the domain
  (an ontology decision), not the extractor.

## What the owner needs to approve
1. Who authors S1, and who annotates it (two people other than the implementer, if possible).
2. Implementing a `gupi.candidate/1` model extractor (new code, a new prompt version).
3. Spending up to $3 of the $10 ledger, with an API key for an account that has credits. A Max
   subscription does not provide them.
4. Optionally: installing llama.cpp and downloading one 4–6 GB model.
5. Optionally, and separately: `rules:v2.1` (D1 and D2 fixes plus the cheap phrasings).
