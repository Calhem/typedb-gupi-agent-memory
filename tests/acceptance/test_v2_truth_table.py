"""Truth-table rows R1-R23 (docs/specialist/v2-truth-semantics.md §4) as proposed acceptance tests.

v1: each row's documented v1 answer is checked against today's `gupi.answering.evaluate`, so the table's
v1 column cannot drift from the code. v1 cannot store negations (no polarity, ADR 0009 Q4), so its rows
run without them, as an extraction would leave them.

v2: the proposed answer and basis. v2 is not implemented (ADR 0009 is proposed), so each v2 test is a
strict expected failure on the missing module `gupi.answering_v2`. When v2 exists, a wrong answer fails as
a normal assertion and a right one reports XPASS, which fails the suite until the marker is removed. The
interface used here (`classify` returning `.answer` and `.basis`) is a proposal too.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace as NS

import pytest

from gupi.answering import evaluate
from gupi.temporal import ValidTime, holds_at


def d(y, m=1, day=1):
    return datetime(y, m, day, tzinfo=timezone.utc)


@dataclass(frozen=True)
class Statement:
    id: str
    valid: ValidTime
    polarity: str = "positive"   # "negative": an explicit negation, covering only `valid`


S = {s.id: s for s in (
    Statement("J1", ValidTime(d(2024, 1), d(2024, 2))),                                    # joined Jan 2024
    Statement("J1x", ValidTime(d(2024, 1, 10), d(2024, 1, 11))),                           # joined 10 Jan 2024
    Statement("L1", ValidTime(to_earliest=d(2024, 3), to_latest=d(2024, 4))),              # left Mar 2024
    Statement("L1b", ValidTime(to_earliest=d(2024, 3, 20), to_latest=d(2024, 3, 21))),     # left 20 Mar 2024
    Statement("K", ValidTime(to_earliest=d(2024, 2), to_latest=d(2024, 3))),               # correction: left Feb
    Statement("CHAT", ValidTime(to_earliest=d(2024, 7))),                                  # still works there, 1 Jul
    Statement("NEG", ValidTime(to_earliest=d(2024, 7)), "negative"),                       # does not work there, 1 Jul
    Statement("NEGS", ValidTime(d(2024, 3), d(2024, 4), to_earliest=d(2024, 9)), "negative"),  # not since Mar, said 1 Sep
    Statement("J3", ValidTime(d(2024, 3), d(2024, 6), to_earliest=d(2024, 9))),            # rejoined spring, there 1 Sep
    Statement("J2", ValidTime(d(2025, 1), d(2025, 2))),                                    # rejoined Jan 2025
    Statement("J2D", ValidTime(d(2025, 1), d(2025, 2), to_earliest=d(2025, 3))),           # ... still there 1 Mar 2025
    Statement("L2", ValidTime(to_earliest=d(2025, 5), to_latest=d(2025, 6))),              # left May 2025
    Statement("ONG", ValidTime(d(2023), d(2024), to_earliest=d(2025, 2))),                 # since 2023, true 1 Feb 2025
    Statement("ONG2", ValidTime(to_earliest=d(2025, 3))),                                  # still true 1 Mar 2025
)}

# row, believed at t, anything recorded by t, v, v1 (answer, assembled), v2 (answer, basis, basis claims)
ROWS = [
    ("R1", "ONG ONG2", True, d(2025, 2, 15), ("TRUE", True), ("PRESUMED", "joined-spell", "ONG ONG2")),
    ("R2", "J1 L2", True, d(2024, 7), ("TRUE", True), ("PRESUMED", "joined-spell", "J1 L2")),
    ("R3", "J1 L1 J2 L2", True, d(2025, 3, 15), ("FALSE", False), ("PRESUMED", "joined-spell", "J2 L2")),
    ("R4", "J1 L1 J2D", True, d(2025, 2, 15), ("CONTESTED", False), ("TRUE", "direct-span", "J2D")),
    ("R5", "J1 L1 J2 L2", True, d(2024, 2, 15), ("FALSE", False), ("PRESUMED", "joined-spell", "J1 L1")),
    ("R6", "J1 L1 J2 L2", True, d(2024, 7, 15), ("FALSE", False), ("FALSE", "termination-continuing", "L1")),
    ("R7", "J1 L1 J2 L2 CHAT", True, d(2024, 7), ("FALSE", False), ("CONTESTED", "conflict", "CHAT L1")),
    ("R8", "J1 L1 J2 L2 CHAT", True, d(2024, 6, 15), ("FALSE", False), ("FALSE", "termination-continuing", "L1")),
    ("R9", "J1 CHAT", True, d(2024, 7), ("UNKNOWN", False), ("TRUE", "direct-point", "CHAT")),
    ("R10", "J1 CHAT", True, d(2024, 5), ("TRUE", True), ("PRESUMED", "joined-spell", "J1 CHAT")),
    ("R11", "J1 L1 CHAT", True, d(2024, 5), ("FALSE", False), ("FALSE", "termination-continuing", "L1")),
    ("R11b", "J1 L1 CHAT", True, d(2024, 7), ("FALSE", False), ("CONTESTED", "conflict", "CHAT L1")),
    ("R12", "J1 K CHAT", True, d(2024, 2, 20), ("TRUE", True), ("UNKNOWN", "window", "K")),
    ("R12′", "J1 L1 CHAT", True, d(2024, 2, 20), ("TRUE", True), ("PRESUMED", "joined-spell", "J1 L1")),
    ("R13", "", False, d(2024, 3), ("NOT_YET_KNOWN", False), ("NOT_YET_KNOWN", "not-recorded", "")),
    ("R14", "", True, d(2024, 2, 15), ("UNKNOWN", False), ("UNKNOWN", "not-believed", "")),
    ("R15", "J1", True, d(2023, 12, 15), ("FALSE", False), ("UNKNOWN", "no-coverage", "")),
    ("R16", "J1 NEG", True, d(2024, 7), ("UNKNOWN", False), ("FALSE", "negation", "NEG")),
    ("R17", "J1 NEG", True, d(2024, 8), ("UNKNOWN", False), ("UNKNOWN", "no-coverage", "")),
    ("R18", "J1 CHAT NEG", True, d(2024, 7), ("UNKNOWN", False), ("CONTESTED", "conflict", "CHAT NEG")),
    ("R19", "ONG NEGS", True, d(2024, 6), ("TRUE", False), ("CONTESTED", "conflict", "NEGS ONG")),
    ("R19b", "ONG NEGS", True, d(2024, 10), ("TRUE", False), ("TRUE", "direct-span", "ONG")),
    ("R20", "J1 J1x CHAT", True, d(2024, 1, 20), ("TRUE", True), ("PRESUMED", "joined-spell", "CHAT J1x")),
    ("R21", "J1 L1 J3", True, d(2024, 7), ("CONTESTED", False), ("TRUE", "direct-span", "J3")),
    ("R22", "J1 L1 J3", True, d(2024, 4, 15), ("FALSE", False), ("UNKNOWN", "window", "J3")),
    ("R23", "J1 L1 L1b", True, d(2024, 3, 25), ("FALSE", False), ("FALSE", "termination-continuing", "L1b")),
]
IDS = [r[0] for r in ROWS]


def v1_claim(s):
    return NS(id=s.id, valid=s.valid, holds_at=lambda at, vt=s.valid: holds_at(vt, at))


@pytest.mark.parametrize("row, believed, recorded, at, v1, v2", ROWS, ids=IDS)
def test_v1_column_matches_todays_code(row, believed, recorded, at, v1, v2):
    claims = [v1_claim(S[i]) for i in believed.split() if S[i].polarity == "positive"]
    result = evaluate(claims, at, recorded)
    assert (result.answer.name, bool(result.assembled)) == v1


@pytest.mark.xfail(raises=ModuleNotFoundError, strict=True, reason="v2 not implemented: ADR 0009 is proposed")
@pytest.mark.parametrize("row, believed, recorded, at, v1, v2", ROWS, ids=IDS)
def test_v2_proposed(row, believed, recorded, at, v1, v2):
    from gupi.answering_v2 import classify  # noqa: PLC0415  (absent until v2 is approved and implemented)

    result = classify([S[i] for i in believed.split()], at, recorded)
    answer, basis, claims = v2
    assert (result.answer.name, result.basis.kind, sorted(result.basis.claims)) == (answer, basis, sorted(claims.split()))


def test_every_row_is_in_the_documented_table():
    from pathlib import Path

    table = (Path(__file__).parents[2] / "docs/specialist/v2-truth-semantics.md").read_text()
    for row, *_ in ROWS:
        assert f"| {row} |" in table
