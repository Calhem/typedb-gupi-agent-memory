# R1: structural fidelity of generic statements

**Failure class (Stage 3B):** a statement grounded word for word whose roles state a different relation.
- **X3-27 / X3-28:** "has opened" + object participant, with the linking words ("… into") left outside the
  roles. Both were formed.
- **X3-19:** an object participant that sits inside the object text ("the same team as …"), turning "shares an
  operator with" into "is operated by". Only the source's hedge stopped it.

**The fix:** `gupi.formation.fidelity.statement_problems`, called by the formation policy (`form.decide`) for every
generic statement, from any extractor and on both paths (`form()` and the candidate store). It reads offsets
only. A statement whose structure it cannot verify **goes to review**; it is never formed by the policy, and never
refused or repaired.

| Check | Sent to review when |
|---|---|
| direct object | an object participant does not follow an occurrence of the predicate with at most a determiner (the, a, an) between them |
| inside object text | any participant lies inside the object text |
| possessor | an object participant is followed by "'s" ("suspended X's licence" is not "suspended X") |
| predicate not found | there is an object participant but the predicate does not occur in the passage (a paraphrase cannot be checked) |

**Order of rules:** unchanged apart from the new reason. Rejection, non-actual modality, copies and unmappable
times still decide first; R1 adds one reason to the existing "needs a review decision" list. A reviewer's approval
still forms the claim.

## Before and after (synthetic fixtures, `tests/unit/test_stage4_r1_structure.py`)
| Case | Before | After |
|---|---|---|
| "X has opened an inquiry into Y", roles X –has opened→ Y | formed | review |
| "X is run by the same crew as the Y set", object Y inside the object text | formed (unless hedged) | review |
| "X has suspended Y's licence", object Y | formed | review |
| object participant with a paraphrased predicate | formed | review |
| "X was bought by Y" with Y as subject, X as object | formed | review |
| "X owns Y"; "X accessed the Y network"; "X has opened an inquiry into Y" (full predicate); object as text only; "X retired" | formed | formed |
| a planned statement | withheld | withheld |
| typed claims (employment, reporting) | unaffected | unaffected |

**Store path** (`tests/integration/test_stage4_integrity.py`): the unverified statement is stored with a `review`
decision and no claim; a reviewer's approval appends `formed` and creates the claim.

## Limits
- **Structural only.** A predicate that misstates the relation while the object follows it directly
  ("X owns Y" for "X once owned Y") is not detected; no semantic check is added.
- **Recall cost:** statements that follow the frozen instructions' "shortest verb" rule with an object participant
  now wait for review. That is intended: the instructions themselves produce the failure class.
- **Passive voice** with the agent as subject always goes to review.
