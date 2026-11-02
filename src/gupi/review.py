"""The review queue and decision history.

The queue holds claims that are hypotheses at a given time (never reviewed, or recorded but not yet
decided), oldest first, with what a reviewer needs to decide: evidence, basis, confidence, alternatives
and conflicts with claims already believed. Decisions are recorded through Memory.review / review_many
and remain historical events.
"""

from dataclasses import dataclass, field

from gupi.status import Status


@dataclass(frozen=True)
class QueueItem:
    claim: object                 # ClaimView
    conflicts: tuple = ()         # gupi.conflicts.Conflict with believed claims
    alternatives: tuple = ()      # ids of competing readings of the same evidence


@dataclass(frozen=True)
class Event:
    at: object
    kind: str
    detail: str
    related: tuple = field(default=())


def queue(claims, at, conflicts_for=None, claim_type=None, method=None, limit=None):
    """Hypotheses at time `at`, oldest first. `conflicts_for(claim)` may attach conflict information."""
    items = []
    for c in claims:
        if c.status_at(at) is not Status.HYPOTHESIS:
            continue
        if claim_type and c.type != claim_type:
            continue
        if method and c.method != method:
            continue
        items.append(QueueItem(c, tuple(conflicts_for(c)) if conflicts_for else (), c.alternatives))
    items.sort(key=lambda i: (i.claim.recorded_at, i.claim.id))
    return items[:limit] if limit else items


def history(claim):
    """Everything that happened to one claim, in recorded order."""
    events = [Event(claim.recorded_at, "recorded", f"{claim.type} claim recorded"
                    + (f" ({claim.basis}, by {claim.method})" if claim.method else ""))]
    for r in claim.reviews:
        events.append(Event(r.recorded_at, r.verdict, f"{r.verdict} by {r.decided_by}"
                            + (f": {r.reason}" if r.reason else "")))
    for other, at in claim.superseded_by:
        events.append(Event(at, "superseded", f"superseded by {other}", (other,)))
    return sorted(events, key=lambda e: (e.at, e.kind))
