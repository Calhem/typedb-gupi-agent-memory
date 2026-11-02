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


# --- periods, for comparing claims (docs/adr/0006) ---
# A period is (start, end), half-open; None means unbounded on that side.

def possible_period(vt: ValidTime):
    """Where the claim could hold at all: from its earliest possible start to its latest possible end."""
    return vt.from_earliest, vt.to_latest


def certain_period(vt: ValidTime):
    """Where the claim certainly holds, or None if nowhere (an unknown start or end leaves no certainty)."""
    if vt.from_latest is None or vt.to_earliest is None or vt.from_latest >= vt.to_earliest:
        return None
    return vt.from_latest, vt.to_earliest


def overlap(a, b):
    """The overlap of two periods, or None."""
    if a is None or b is None:
        return None
    start = a[0] if b[0] is None else b[0] if a[0] is None else max(a[0], b[0])
    end = a[1] if b[1] is None else b[1] if a[1] is None else min(a[1], b[1])
    if start is not None and end is not None and start >= end:
        return None
    return start, end


def false_side(vt: ValidTime, at):
    """Why a claim says FALSE at `at`: "before" its earliest start, "after" its latest end, or None."""
    if vt.from_earliest is not None and at < vt.from_earliest:
        return "before"
    if vt.to_latest is not None and at >= vt.to_latest:
        return "after"
    return None


def same_spell(c: ValidTime, x: ValidTime, side):
    """Does claim c's FALSE on `side` really bear on claim x, i.e. are they certainly the same spell?

    "after": x certainly started before c's end window, so x continuing past c's end disagrees with c.
    "before": x certainly lasted past c's start window, so x holding before c's start disagrees with c.
    Otherwise x may be a different spell (an earlier or later period), and c's FALSE says nothing about it.
    """
    if side == "after":
        return x.from_latest is not None and c.to_earliest is not None and x.from_latest < c.to_earliest
    if side == "before":
        return x.to_earliest is not None and c.from_latest is not None and x.to_earliest > c.from_latest
    return False
