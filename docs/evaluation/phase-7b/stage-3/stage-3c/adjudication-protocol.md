# Stage 3C adjudication protocol

## The package (private: `gupi-stage3-private/stage3c/adjudication-package/`)
**Generated from the frozen data:** the passages, gold v1, the raw responses, the Stage 3B score and the
reconstructed formation decisions. It contains **no conclusion or suggested correction from the gold's author.**

| File | Contents |
|---|---|
| `items.md` | 19 items, each with the passage and its metadata (and earlier thread turns), the frozen gold assertion(s), the raw model assertion, the scorer's mechanical classification, any frozen severe-error label, the formation decision and reason, the model's own reported problems, and six questions |
| `format-*.md` | the response format and extraction instructions exactly as the model saw them, and the gold annotation contract |
| `decisions.csv` | one blank row per item |
| `README.md` | the reviewer's instructions |

**The items:**
- **1–8:** the 7 partial matches and the 1 overlapping, unmatched candidate.
- **9:** the matched candidate with a severe-error label.
- **10–12:** the 3 missed assertions under dispute.
- **13–19:** supplementary cases for the severe errors and failure modes (the question, the surname and attribution
  cases, the contradiction, the bare retraction, two claimant kinds).

**The six questions per item:**
1. **Meaning:** is the meaning of the source preserved?
2. **Structure:** are the subject, predicate and object right?
3. **Attribution:** are the claimant identity and attribution preserved?
4. **Modality and time:** are modality, uncertainty and temporal meaning preserved?
5. **Classification:** one of:
   - exact
   - semantically correct alternative
   - partial
   - incorrect
   - unsupported
   - appropriate abstention
   - missed

   Or a gold error, with a reason.
6. **Admission:** should it have been formed, reviewed, rejected or withheld?

## Who may adjudicate
| Reviewer | Allowed | Label |
|---|---|---|
| A person who did not develop GUPI or write the gold | yes, preferred | independent human adjudication |
| The owner | yes, if no one else is available | owner adjudication: not independent of the project, though independent of the gold |
| A separate Claude session given only the package | **only with the owner's approval** | model-assisted adjudication: never independent human verification |
| The Stage 3A/3B/3C session (the gold's author) | **no** | – |

## From decisions to results
1. **Freeze the decisions:** record the reviewer's sheet as written, commit it privately, and hash it.
2. **Build a new gold version, gold v2:**
   - **Gold errors:** each decision marked "gold error" becomes a change.
   - **Equivalent alternatives:** each "semantically correct alternative" is recorded as an accepted alternative
     for that gold assertion.
   - **Gold v1 is never edited.**
3. **Rescore both systems,** Claude and `rules:v2.1`, against gold v2 with the frozen scorer. Label the result
   "adjudicated (gold v2)". The original figures against gold v1 stay as reported.
4. **Explain every change:** for each changed classification, give the item, the decision and the reason.
5. **Clear a severe-error label** only by an explicit decision with a reason. A label the reviewer leaves undecided
   stays.

**The scorer change step 3 may need:** recording accepted alternatives needs a small scorer addition, which is
proposal R7. Until that is approved, an adjudicated result is computed by listing the decisions next to the
frozen scorer's output, not by changing the scorer.
