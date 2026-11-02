# Phase 3 proposal: temporal reconciliation and identity

Goal (gate, from the brief): correction, retraction, contradictory sources, retroactive updates and
identity merge/split; observation kept distinct from accepted knowledge; history preserved; tests for
as-of valid time and as-of recorded time, including conflicting sources and uncertain dates.

Much of the bitemporal core exists (Phase 1). Phase 3 adds the decisions people make on top of it:

1. **Review queue.** List hypotheses awaiting review (by context, type, basis, confidence), show each with
   its evidence, alternatives and competing claims, and record accept/reject/retract in batches.
2. **Conflict detection.** Find believed claims about the same proposition (or the same functional
   attribute, e.g. a job title at one employer) whose valid times overlap with different values, and
   report them as CONTESTED with both sides, without choosing a winner automatically.
3. **Identity candidates.** Propose `identity` claims between conversation-scoped referents (same name and
   kind, shared context), scored and explained, never merged automatically. Accepting one makes queries
   treat the referents as one; rejecting or retracting it splits them again, with history kept.
4. **Reversible supersession and alternatives policy.** Allow a supersession to be retracted (a decision
   with its own time), and make accepting one alternative reading mark the others for review.
5. **Retroactive and late-arriving updates.** Tests where corrections arrive out of order, claims about
   the past arrive after claims about the present, and an identity merge changes earlier answers only for
   belief times after the merge.
6. **Optional: persistence presumption.** If wanted, answer "presumably still true" for open-ended claims,
   always labelled as a presumption and never as TRUE.

Decisions needed from the owner:
- Whether a minimal command-line review tool is wanted in Phase 3, or reviews stay in Python.
- Whether to spend part of the $10 on the Claude evaluation before Phase 3 (needs an API key), so Phase 3
  fixtures can include LLM-extracted claims.
