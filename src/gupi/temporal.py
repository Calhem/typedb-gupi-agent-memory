"""Valid-time semantics (docs/adr/0003-temporal-semantics.md).

A fact holds on the half-open interval [start, end). Each boundary is only known to lie in a window
[earliest, latest): earliest == latest means the boundary is exact, and a missing bound means unbounded
on that side. With no end bounds at all the end is unknown, which is not the same as "still true".

`holds_at` answers for one claim with three values: TRUE, FALSE or UNKNOWN. `combine` answers for all the
claims believed about a proposition, adding NOT_YET_KNOWN and CONTESTED.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Truth(Enum):
    TRUE = "true"
    FALSE = "false"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ValidTime:
    from_earliest: datetime | None = None
    from_latest: datetime | None = None
    to_earliest: datetime | None = None
    to_latest: datetime | None = None


def holds_at(vt: ValidTime, at: datetime) -> Truth:
    if vt.from_earliest is not None and at < vt.from_earliest:
        return Truth.FALSE  # certainly not started
    if vt.to_latest is not None and at >= vt.to_latest:
        return Truth.FALSE  # certainly ended
    started = vt.from_latest is not None and at >= vt.from_latest
    not_ended = vt.to_earliest is not None and at < vt.to_earliest
    return Truth.TRUE if started and not_ended else Truth.UNKNOWN


class Answer(Enum):
    """The answer to "did this hold at valid time v, as GUPI believed at transaction time t?"."""

    TRUE = "true"                    # a believed claim says it held at v
    FALSE = "false"                  # a believed claim says it did not hold at v
    UNKNOWN = "unknown"              # claims were recorded by t, but none believed decides v
    NOT_YET_KNOWN = "not-yet-known"  # nothing about it had been recorded by t
    CONTESTED = "contested"          # believed claims disagree: some say TRUE, some FALSE


def combine(truths, anything_recorded):
    """Combine the per-claim truths of the claims believed at t about one proposition.

    `anything_recorded` says whether any claim about the proposition (believed or not) had been recorded
    by t. Absence of a claim never counts as FALSE: GUPI does not assume a closed world.
    """
    truths = set(truths)
    if not anything_recorded:
        return Answer.NOT_YET_KNOWN
    if Truth.TRUE in truths and Truth.FALSE in truths:
        return Answer.CONTESTED
    if Truth.TRUE in truths:
        return Answer.TRUE
    if Truth.FALSE in truths:
        return Answer.FALSE
    return Answer.UNKNOWN
