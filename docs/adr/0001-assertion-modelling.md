# ADR 0001: Claims are typed relations, one per attestation, with decisions kept separately

Status: accepted (Phase 0 approved; revised before Phase 1), 2026-11-02

## Context
GUPI must store claims about the world with provenance, confidence, review status and bitemporal
history, while keeping TypeDB's typed n-ary relations meaningful. Two standard shapes:

**A. Assertion-as-entity (reification).** An `assertion` entity points at its subject, predicate and
object through generic link relations (`asserts (assertion, subject)`, ...).

**B. Assertion-as-relation.** The claim *is* a typed domain relation, e.g.
`reporting (report: $alice, manager: $bob)`, and that relation instance owns its time bounds and plays
roles in `evidence`, `review` and `supersession`. Every domain relation subtypes an abstract `claim`.

| Concern | A: entity | B: relation |
|---|---|---|
| Role semantics | lost or rebuilt by hand (generic slots; n-ary claims need a role table) | native: the schema's own roles, checked by TypeDB |
| Querying a domain claim | joins through the reification layer | a normal pattern: `reporting (report: $a, manager: $m)` |
| Provenance, review, supersession | entity plays roles | relation plays roles (verified: abstract relations can play roles; subtypes inherit) |
| Claims about an attribute value | natural | a typed relation that owns the value (`employment ... has job-title`) |
| Generic tooling ("all claims") | trivial | `$c isa claim` through inheritance (verified) |

## Decision
Use **B**, with one refinement from the pre-Phase-1 review: **a claim is one attestation**, not a
deduplicated fact. Two sources saying the same thing produce two claims. Each claim has its own
`gupi-id` (derived from its content and evidence), its own evidence, and its own reviews. Claims about
the same proposition share a `proposition-key` (claim type + role players), so they can be found together.

Layers, each its own type:
- `observation`: what a source said, verbatim. Never edited.
- `claim` subtypes: one attestation. Inserted once, never mutated. A **hypothesis** until accepted.
- `evidence`: claim -> observation, with a character span.
- `review`: a decision (accepted / rejected / retracted). Historical: the latest review recorded by time T
  sets the status at T (ADR 0003).
- `supersession`: a correction; the old claim stays.
- `alternatives`: competing readings of the same evidence.
- `identity (same, same)`: a claim, so identity merges are reviewable and reversible (logic in Phase 3).

## Review against the four scenarios
Each is a live test in `tests/integration/test_claims.py`.

| Scenario | How it is represented | What the test shows |
|---|---|---|
| Several independent sources assert the same fact | one claim per source, same `proposition-key` | each claim and its source retrievable on its own; retracting one leaves the other believed |
| Contradictory claims | separate claims kept side by side; nothing is overwritten | competing job titles both returned with their sources; opposite time bounds give `CONTESTED` |
| Retrospective correction | new claim + `supersession` | "now" and "as believed in March" differ; the old claim and its evidence remain |
| Several interpretations of one observation | one claim per reading, same evidence span, linked by `alternatives` | both are hypotheses (answer `UNKNOWN`, not `FALSE`) until reviewed; each lists the other |

The ontology changed as a result: `fact` was renamed `claim` (it may be false), and `proposition-key`,
`alternatives` and decision ids were added.

## Consequences
- "Is X true?" aggregates over claims (`Memory.ask`), rather than reading one record.
- Attribute-valued claims need a typed carrier relation per claim type (e.g. `employment` owning
  `job-title`). Whether GUPI should ship generic carriers is a Phase 2 question.
- Nothing in the schema stops a caller accepting two alternatives at once; policy is Phase 3.
