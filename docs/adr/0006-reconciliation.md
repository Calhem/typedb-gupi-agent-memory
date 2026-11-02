# ADR 0006: Reconciliation: review, conflicts, identity and reversible corrections

Status: accepted (Phase 3), 2026-11-02

## Review
- The review queue is every claim whose status at time t is HYPOTHESIS, oldest first, with its evidence,
  basis, confidence, alternatives and conflicts against claims believed at t. It can be rebuilt for any
  past t. Decisions are reviews (historical events, reviewer required); `review_many` records a batch in
  one transaction.

## Spells: when a FALSE counts
A claim says the proposition held during its period and did not hold just outside it. But "since 2024"
does not deny an earlier spell, and "for all of 2022" does not deny a later one. So a claim's FALSE
before its start (or after its end) only counts against another claim that is certainly the **same
spell**: one that certainly lasted past that start (or certainly started before that end). Otherwise the
other claim may describe a different period, and the FALSE is ignored in `ask()` (the answer is then
TRUE or UNKNOWN from the other claim, never a manufactured FALSE or CONTESTED). Overlapping disagreements
about one spell remain CONTESTED.

## Conflicts (`gupi.conflicts`)
For two claims about the same proposition (after merging accepted identities):

| Class | Meaning |
|---|---|
| contradiction | one is certainly true where the other, about the same spell, is certainly false; or a single-valued attribute has two values both certainly true at once |
| differing-evidence | compatible but different detail: other bounds or precision, or values that may be sequential (e.g. a promotion) |
| corroboration | same bounds and values from different evidence |
| separate-periods | possible periods do not overlap |

Domain packs declare rules in `constraints.json`: single-valued attributes (`employment.job-title`) and
one-player-at-a-time roles (one manager per report at a time), which also yield contradictions across
propositions. Nothing is resolved automatically.

## Identity
`suggest_identities()` proposes same-kind referents (same name in different conversations, or a first
name and a full name in one conversation) as `identity` claims: hypotheses, basis inferred, with the
reason and the mentions as evidence. Pairs with any identity claim already are not suggested again.
Only an accepted identity merges referents, in `ask()` and conflict detection, for belief times from its
acceptance on; retracting it splits them again without rewriting earlier answers. Merging is
transitive within the accepted identities.

## Reversible corrections and order
- Supersessions can be reviewed (migration core/0005). One is in force from its recording until a
  rejection or retraction of it with no later acceptance; ties count as withdrawn. `believed_at`
  (core/0006, redefined) and `gupi.status` implement the same rule and are tested against each other.
- Valid time never depends on arrival order. `suggest_supersessions()` proposes newer-replaces-older among
  believed claims from the same source ordered by **observed-at** (when the source said it), never by
  when GUPI received it, and skips values that may be sequential. It applies nothing.
- `Memory` refuses to work on a database with pending migrations.
