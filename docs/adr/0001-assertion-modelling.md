# ADR 0001: Assertions are typed relations (assertion-as-relation), with decisions kept separately

Status: proposed (Phase 0), 2026-11-02

## Context
GUPI must store claims about the world with provenance, confidence, review status and bitemporal
history, while keeping TypeDB's typed n-ary relations meaningful. Two standard shapes:

**A. Assertion-as-entity (reification).** An `assertion` entity points at its subject, predicate and
object through generic link relations (`asserts (assertion, subject)`, ...).

**B. Assertion-as-relation.** The claim *is* a typed domain relation, e.g.
`reporting (report: $alice, manager: $bob)`, and that relation instance owns its time bounds and plays
roles in `evidence`, `review` and `supersession`. Every domain relation subtypes an abstract `fact`.

## Comparison

| Concern | A: entity | B: relation |
|---|---|---|
| Role semantics | lost or rebuilt by hand (generic `subject`/`object` slots; n-ary claims need a role table) | native: roles are the schema's own roles, checked by TypeDB |
| Querying a domain fact | joins through the reification layer | a normal pattern: `reporting (report: $a, manager: $m)` |
| Several competing claims about the same players | natural | natural: TypeDB 3 keeps distinct relation instances with the same players (verified) |
| Provenance, review, supersession | entity plays roles | relation plays roles (verified: an abstract relation can play roles, subtypes inherit) |
| Bitemporal attributes | on the entity | on the relation (verified: relations own attributes, inherited from `fact`) |
| Claims about an attribute ("Alice's title is CTO") | natural | modelled as a small typed relation that owns the value (`employment ... has job-title`); a domain author must create one |
| Generic tooling (one query for "all facts") | trivial | `$f isa fact` works through inheritance (verified) |
| Domain extensibility | no schema per claim type: weakly typed | one `sub fact` relation per claim type: strongly typed |

## Decision
Use **B**. A fact is an instance of a subtype of the abstract relation `fact`, so domain meaning and role
semantics stay native, and generic machinery works on `fact`.

Separate layers, each its own type:
- `observation` (entity): what a source said, verbatim. Never edited.
- `fact` (relation subtypes): a claim. Inserted once and never mutated. It is a **hypothesis** until a
  `review` with verdict `accepted` exists; rejection and retraction are also reviews.
- `evidence` links a fact to the observations (with spans) that support it.
- `supersession` links a corrected fact to its replacement. Old facts are kept.
- Identity merges are facts too (`identity (same, same)`), so they can be reviewed and reversed.

Every decision carries its own `recorded-at`, so "what did we believe at time T" is answerable
(`believed_at` in schema/functions.tql).

## Consequences
- Attribute-valued claims need a typed carrier relation; GUPI should ship a small set of core carriers
  (Phase 1) so domain authors rarely need to write one.
- Status is derived (latest review), not stored on the fact; queries pay a small join for it.
- If a future need for statements *about* reviews appears, reviews can play roles too, without
  changing facts.
- Verified in `tests/integration/test_core_ontology.py`.
