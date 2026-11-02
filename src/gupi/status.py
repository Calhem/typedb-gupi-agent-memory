"""A claim's status at a transaction time, derived from its history of decisions.

Reviews are events. The latest review recorded by time t decides the status at t, so a claim rejected in
May and re-accepted in July is believed from July on. When an acceptance and a rejection or retraction
carry the same timestamp, the non-acceptance wins (the conservative reading). A supersession recorded by t
overrides any review. This must agree with `believed_at` in schema/core/0002_functions.schema.tql
(tests/integration/test_claims.py checks that it does).
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Status(Enum):
    NOT_RECORDED = "not-recorded"  # GUPI had not recorded the claim yet
    HYPOTHESIS = "hypothesis"      # recorded, never reviewed
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    RETRACTED = "retracted"
    SUPERSEDED = "superseded"


@dataclass(frozen=True)
class ReviewEvent:
    verdict: str
    recorded_at: datetime
    decided_by: str | None = None
    reason: str | None = None
    id: str | None = None


def status_at(recorded_at, reviews, supersession_times, t):
    if t < recorded_at:
        return Status.NOT_RECORDED
    if any(s <= t for s in supersession_times):
        return Status.SUPERSEDED
    seen = [r for r in reviews if r.recorded_at <= t]
    if not seen:
        return Status.HYPOTHESIS
    latest = max(r.recorded_at for r in seen)
    verdicts = {r.verdict for r in seen if r.recorded_at == latest}
    for verdict, status in (("retracted", Status.RETRACTED), ("rejected", Status.REJECTED)):
        if verdict in verdicts:
            return status
    return Status.ACCEPTED


def supersession_in_force(recorded_at, reviews, t):
    """A supersession applies from when it was recorded until a rejection or retraction of it (recorded by t)
    with no later acceptance; ties count as withdrawn. Reviews make corrections reversible."""
    if t < recorded_at:
        return False
    seen = [r for r in reviews if r.recorded_at <= t]
    if not seen:
        return True
    latest = max(r.recorded_at for r in seen)
    return all(r.verdict == "accepted" for r in seen if r.recorded_at == latest)
