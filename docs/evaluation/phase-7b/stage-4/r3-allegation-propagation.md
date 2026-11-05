# R3: allegation propagation

**Failure class (Stage 3B, X3-09):** a fact drawn from inside an allegation ("The complaint alleges that the
company's former officer, …, approved …") was formed as `certain`. The allegation flag sat on the statement the
model extracted, not on the employment drawn from the same clause, and formation looks only at a candidate's own
commitment.

**The fix:** in the offline model interface (`model:candidate-v1.1`), an assertion is treated as inside an
allegation when either:
- **its evidence lies inside the evidence of another assertion the model marked `allegation`**, or
- **its sentence has an allegation cue** read by code: allege(s/d/dly/ation), accuse(d/s/ation), purported(ly).

Then:
| What | Rule |
|---|---|
| commitment | `certain` becomes `unknown` (flag `commitment-downgraded`); a weaker commitment is kept as stated |
| attribution | inside a marked allegation, an assertion with no claimant of its own (`direct`) takes the alleger's attribution (mode, claimant, kind); a claimant the model gave is kept |
| flags | `allegation-inherited` (inside a marked allegation) or `allegation-context` (a cue in the sentence) |

Formation already sends `unknown` commitment to review ("hedged by the source"), so the fact waits for a
reviewer. **What a document alleges stays distinct from what GUPI holds as established:** if a reviewer approves
it, the claim is stored with the alleger as asserter, mode `reported` and commitment `unknown`, never as the
author's unqualified statement. No new inference is made: the evidence span and the claimant are the ones
already in the response.

## Before and after (synthetic, `tests/unit/test_stage4_r3_allegations.py`, `tests/integration/test_stage4_integrity.py`)
| Case | Before | After |
|---|---|---|
| employment inside "The lawsuit alleges that …", no claimant | formed, certain, direct | **review**; unknown; reported by "The lawsuit" |
| the same, with the model's own claimant | formed, certain | review; unknown; claimant kept |
| "X, the finance director at Y, is accused of …", nothing marked by the model | formed | review (`allegation-context`) |
| commitment `probable` inside an allegation | review | review, still `probable` |
| a fact in a different sentence from the allegation | formed | formed |
| the allegation statement itself | review | review |
| a reviewer approves the embedded fact | – | claim: reported, commitment unknown |

Time phrases, evidence spans and the author in `via` are unchanged by the inheritance.

## Limits
- **Lexical and span-based:** an allegation worded without a cue, and not marked by the model, is not seen
  ("the filing says that …").
- **Over-inclusive by design:** every assertion in a sentence with a cue goes to review, including a denial
  ("… denies the allegations"), which is a reported statement of its own.
- **"former" is still not represented** (R4, not in this stage): an approved embedded employment is still timeless.
