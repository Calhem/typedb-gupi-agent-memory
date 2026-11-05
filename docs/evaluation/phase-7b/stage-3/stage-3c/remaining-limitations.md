# Remaining limitations and unresolved decisions (Stage 3C)

## What this stage could not settle
1. **No independent human adjudication.** No reviewer outside GUPI and the gold was available.
   - **Update (2026-11-05):** the 19 items were decided by a model-assisted review (ChatGPT). Its exploratory
     figures are in [results-model-assisted.md](results-model-assisted.md): within the bounds below, with 3 formed
     severe errors remaining.
   - **Still open:** human verification of those decisions, and the gold change for item 9, which the reviewer
     flagged without specifying.
   - **Bounds given before the review:** precision 21/30–29/30, recall 21/39–29/39 (29/36 if the gold changes),
     formed severe errors 0–3.
2. **The gold's author wrote the diagnosis.** The analysis rests on source text, frozen documents and code. Even so,
   the author's view of its own gold is not neutral, which is why every gold-dependent classification is left open.
3. **The adjudication is model-assisted.** With the owner's approval it was done by ChatGPT, not a Claude
   session, and is labelled model-assisted adjudication, not independent verification.
4. **The isolation is qualified.** The frozen audit failed on the desktop transcript format, and that result is
   preserved. The tool-call inspection supports the run but does not replace the audit.
5. **One run, one corpus, one author and one model family.** The run is also a second attempt: attempt 1 was
   aborted with no responses, and is documented.
6. **D's answering-v2 hypothesis is untested.** Whether a timeless claim can contribute to a presumed period is
   open (R6).
7. **This is not an integration test.** Every write was approved by a person.

## Decisions for the owner
| Decision | Options |
|---|---|
| Who adjudicates | an independent person (preferred); the owner; or an approved model-assisted session, labelled as such |
| Whether R1–R3 (essential) go ahead before any automated integration | approve design, ask for changes, or defer |
| R4–R6 (extraction quality) | approve or defer |
| R7–R10 (evaluation) | approve or defer; R10 (an externally written corpus) is the main gap before adoption |
| Whether to merge Stages 3A, 3B and 3C | not before review |

## Existing limitations these results touch
| Limitation | Case |
|---|---|
| S1 (problem reports not stored) | X3-17 |
| S8 (same-named people share a referent) | X3-29 |
| L4 (copy detection needs the same wording) | X3-27/28 |
| L5 (inferred assertions refused) | X3-07 |
| L2/L3 (corrections never applied automatically) | X3-12 |
