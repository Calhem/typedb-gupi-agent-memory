# Phase 3 plan: reconciliation, review and identity (revised after the owner's priorities)

Goal (gate, from the brief): correction, retraction, contradictory sources, retroactive updates and
identity merge/split; observation kept distinct from accepted knowledge; history preserved; tests for
as-of valid time and as-of recorded time, including conflicting sources and uncertain dates.

## Owner direction (2026-11-02)
Defer the live Claude evaluation; use the offline rule extractor and deterministic fixtures. Keep the
extraction benchmarks unchanged, and never present offline results as evidence of LLM performance.
Priorities, in order: review queue and historical decisions; conflict detection separating genuine
contradictions from differing evidence; suggested identity resolution without automatic merging;
reversible corrections and out-of-order updates; a minimal review CLI.

## Design
1. **Review queue.** Claims whose status now is HYPOTHESIS (oldest first), each shown with its evidence,
   basis, confidence, alternatives and any conflicts it would create. Decisions can be recorded one at a
   time or as a batch in one transaction; each stays a historical event with its own recorded-at.
2. **Conflicts** between claims believed at a time t, pairwise, classified as:
   - *contradiction*: both cannot be true. Either one claim is certainly true at some moment where the
     other is certainly false, while their possible periods overlap; or, for an attribute or role the
     domain pack declares single-valued (`constraints.json`, e.g. one job title per job, one manager at a
     time), two different values are both certainly true at the same moment.
   - *differing evidence*: compatible claims that disagree in detail (different precision, one end known
     and the other not, different values where they do not certainly overlap in time, e.g. a promotion).
   - *corroboration*: the same proposition with the same bounds and values from different evidence.
   - *separate periods*: possible periods that do not overlap (e.g. two spells of employment).
   Nothing is resolved automatically; conflicts are reported with both sides.
3. **Fix found while designing:** today `ask()` returns CONTESTED for two separate periods, because a claim
   says FALSE before its own start. A FALSE now only counts against a TRUE when the two claims' possible
   periods overlap. Genuine contradictions (overlapping periods) stay CONTESTED. Phase 1 tests keep passing.
4. **Identity suggestions.** Candidates between referents of the same kind: same normalised name in
   different conversations, or a first name matching a full name in the same conversation. Each becomes
   an `identity` claim as a *hypothesis* (basis inferred, with the mentions' observations as evidence and the
   reasons in the run record). Only an accepted identity merges referents in answers, from its acceptance
   time on; rejecting or retracting it later splits them again, and earlier belief times are unchanged.
5. **Reversible corrections.** Supersessions become reviewable: retracting a supersession (a review on
   it, with its own time) makes the replaced claim believed again from then on. `believed_at` and the
   Python status are updated together (new migration, `redefine`).
6. **Out-of-order updates.** Valid time never depends on arrival order. Supersession *suggestions* order
   claims by when the source said them (observed-at), not when GUPI received them, so a late-arriving old
   message never replaces newer information. Tests cover corrections that arrive before, and old claims
   that arrive after, the claims they relate to.
7. **CLI** (`gupi`, standard library only): `queue`, `show`, `accept` / `reject` / `retract`, `conflicts`,
   `identities`, `supersede` / `unsupersede`, `ingest` (a conversation file through the offline extractor).
   Reviewer name required on every decision.

Out of scope: retrieval and answer generation (Phase 4), the Claude evaluation (deferred), a persistence
presumption, a UI.
