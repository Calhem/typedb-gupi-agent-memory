# Success criteria and stopping rules (proposed; to be frozen before any scored run)

**What these are:** decision rules for this experiment, set before any model output is seen. They are not
estimates of general performance.
- **Where they apply:** S1, the specialist passages, decides. S2 is reported, and can veto only on
  evidence-integrity grounds (the "Hard failures" section below).
- **What is compared:** each system against Baseline A, `rules:v2.1`, on the same frozen gold.

## Thresholds for Candidate B (`model:candidate-v1`) on S1
| # | Criterion | Threshold | Why |
|---|---|---|---|
| T1 | recall improvement over `rules:v2.1` | ≥ **+0.20** absolute (matched gold groups), **and** an exact McNemar test on paired gold groups with p < 0.05 | a smaller gain would not justify a model dependency, and could not be distinguished at this size |
| T2 | precision | ≥ **0.85** (with gold omissions excluded, as specified) | a model that over-extracts fills review queues and memory with noise |
| T3 | unsupported-claim rate | ≤ **5%** of B's candidates | |
| T4 | invalid-output rate (`invalid-model-output` + `grounding-failure` + `ambiguous-span`) | ≤ **5%** of passages | above this, the pipeline cannot be relied on |
| T5 | attribution fidelity on matched pairs: mode and claimant both right | ≥ **0.85** | |
| T6 | temporal fidelity on matched pairs with a time: expression preserved ≥ **0.95**, kind right ≥ **0.85** | | |
| T7 | polarity right ≥ **0.95**; modality and commitment both right ≥ **0.80** | | |
| T8 | formation compatibility: B's candidates passing schema-aware validation | ≥ **0.95** | |
| T9 | cost | ≤ **$0.03 per passage** (settled actuals) | |
| T10 | latency | p95 ≤ **30 s per passage**, synchronous | |

**The verdict:**
- **"Materially improves GUPI":** every threshold T1–T10 is met, and the "Hard failures" section below is
  not triggered.
- **Partly met:** recall is met but fidelity is not, or the reverse. The verdict is "not adopted". The report
  says which, so that the next step targets it.

## Hard failures: evidence integrity (any one stops adoption, whatever the recall)
These are the **severe errors**:
- **Invented entity:** a participant or claimant not in the text, or a referent the text does not support.
- **Unsupported certainty:** `certain` or `direct` where gold is hedged, reported, rumour or allegation.
- **False independent corroboration:** a forwarded or repeated assertion presented as independent.
- **Invented time:** a date or precision not justified by the text.

**When adoption stops:**
- **H1:** severe errors exceed **3 per 100 candidates** on S1, or on S2.
- **H2:** **any** severe error is **formed** (admitted without review) in more than **2** passages of S1 and
  S2 combined. In memory, a formed severe error is a confident false belief.
- **H3:** any pronoun is formed as a named participant (the D1 regression).

## Stopping rule during the scored run
This rule is for safety only, so the run can be abandoned but never tuned.
- **When it triggers:** after the first 10 S1 passages are processed (in the frozen order), if the severe
  errors found by the deterministic checks alone reach **5**. Those checks are grounding, pronouns,
  claimants not in the text, and forwarded-as-direct.
- **What happens:**
  - The run stops, and the result is reported as **failed on evidence integrity**, with the partial results
    kept.
  - No prompt change is made and the run is not resumed. A new prompt version would be a new experiment, on
    a new frozen corpus.

## Statistical limits (stated now, so the results are not over-read)
- **With about 100 gold assertions** in S1, the 95% interval around a proportion is about **±10 points** near
  0.5, and about ±7 near 0.85.
  - **What that means:** a precision of 0.86 is consistent with a true value anywhere from about 0.78 to
    0.92.
- **Rare events** (severe errors) cannot be shown to be rare at this size:
  - **The bound:** zero errors in 150 candidates still leaves a 95% upper bound of about 2%.
  - **What the thresholds are for:** they catch frequent failure; they cannot certify reliability.
- **Correlated items:** 40 passages by a few authors share style and habits, so the assertions are not
  independent. Intervals computed per assertion are optimistic. A passage-level bootstrap is reported
  alongside them.
- **What the results support:** this corpus and this prompt. They support no other domain or model version,
  and no generalisation to the conversation datasets.
