"""Valid-time semantics (docs/adr/0003-temporal-semantics.md).

A fact holds on the half-open interval [start, end). Each boundary is only known to lie in a window
[earliest, latest): earliest == latest means the boundary is exact, and a missing bound means unbounded
on that side. With no end bounds at all the end is unknown, which is not the same as "still true".

`holds_at` answers with three values: TRUE, FALSE or UNKNOWN.
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
