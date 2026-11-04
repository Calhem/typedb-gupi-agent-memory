# D3: correction targets that are not established

**The problem (Stage 2A):**
- **The format:** `gupi.candidate/1` required every correction relation to name a target.
- **So:** a correction whose target the source does not establish ("Sorry, she joined in April") could not be
  expressed at all. It was dropped before review, so the evidence was lost.

**The fix (commit `538e6c1`; the offline interface in `aca7311`):**
- **In the format:** a format-1.1 relation of kind `corrects`, `retracts` or `updates` may have
  `target: null`, meaning the source states a correction but not what it corrects. `contradicts` still needs
  a target.
- **In formation (formation:v1, `decide`):** every stated correction, retraction or update goes to
  **review**. A null target adds the reason "a stated correction whose target is not established".
  - **Nothing is superseded or changed automatically,** whatever the reviewer later decides about the
    candidate itself.
- **The suggestion (`_suggest_corrections`):**
  - **What it lists:** every believed claim in the same conversation with the same type and participants.
  - **What it records:** never `resolved` for a null target. It is `missing` when there is no plausible
    target, and `ambiguous` otherwise, even when only one claim is plausible.
  - **The note:** "its target is not established by the source: listed for review, never resolved".
  - **What it never offers:** claims that have been superseded, or claims from other conversations.
- **The reviewer's tool (`store.assign_correction_target(memory, candidate, claim, reviewer, reason)`):**
  - **What it records:** a new append-only `correction-suggestion`, `resolved`, whose reason names the
    reviewer and their reason. The earlier suggestion stays in the history.
  - **What it refuses:**
    - no reviewer
    - an unknown candidate
    - a candidate with no stated correction
    - a claim id that is not in memory, or is no longer believed, or is of a different type
  - **Repeating it** has no further effect.
  - **It still supersedes nothing.** Acting on the correction remains a separate, explicit memory operation.
- **No schema change:** the existing `target-resolution` values are enough.
- **The offline interface (`model:candidate-v1.1`):**
  - **One match:** exactly one matching earlier candidate gives the target.
  - **Otherwise:** a null target with the flag `correction-target-unresolved`, where the format 1.0 interface
    gave an outcome and no candidate.

## Tests (before the fix, 11 of 12 failed with a TypeError on the null target: `before/d3-original-failures.txt`)
| Required case | Test | Result |
|---|---|---|
| explicit target | `test_an_explicit_target_is_resolved_and_reviewed` | review; suggestion `resolved` to that claim |
| no target | `test_no_identified_target_is_kept_and_reviewed_without_inventing_one` | review; null target kept; evidence inspectable; `missing` |
| one plausible target | `test_one_plausible_target_is_listed_but_not_resolved` | listed, `ambiguous`, not resolved |
| several targets | `test_several_plausible_targets_are_all_listed` | all listed, `ambiguous` |
| a retraction | `test_a_retraction_without_a_target` | review, `missing` |
| a target outside the conversation | `test_a_target_in_another_conversation_is_not_matched` | not offered |
| a pronoun | `tests/unit/test_model_candidate.py::test_a_correction_whose_subject_is_a_pronoun_is_never_resolved` | no candidate (`ambiguous-reference`); no target guessed |
| superseded | `test_a_superseded_assertion_is_not_offered` | not offered |
| two corrections | `test_two_corrections_of_the_same_assertion` | both reviewed; nothing changed |
| a target assigned later | `test_a_reviewer_assigns_the_target_later_and_it_is_audited` | new resolved suggestion naming the reviewer; history kept; idempotent; nothing superseded |
| refusals | `test_target_assignment_refuses_what_it_cannot_justify` | unknown claim, no correction, no reviewer all refused |
| approval changes nothing | `test_approving_an_unresolved_correction_changes_no_prior_claim` | the earlier claim stays believed |
| resubmission | `test_resubmission_is_idempotent` | one decision, one suggestion |

All are in `tests/integration/test_d3_null_targets.py` unless a path is given.

**Where it shows:** the developer fixtures. DEV-126, a retraction whose target the recorded response cannot
match, now reaches review with a null target instead of stopping at the extractor (compatibility-results.md).
