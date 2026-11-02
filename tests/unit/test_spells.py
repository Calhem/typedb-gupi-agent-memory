from datetime import datetime, timezone
from types import SimpleNamespace as NS

from gupi.answering import evaluate
from gupi.temporal import Answer, ValidTime, holds_at, same_spell


def d(y, m=1, day=1):
    return datetime(y, m, day, tzinfo=timezone.utc)


def claim(cid, vt):
    return NS(id=cid, valid=vt, holds_at=lambda at, vt=vt: holds_at(vt, at))


JOINED_JAN = ValidTime(d(2025, 1), d(2025, 2))                 # "joined in January", end unknown
LEFT_MAY = ValidTime(to_earliest=d(2025, 5), to_latest=d(2025, 6))  # "left in May", start unknown


def test_window_bounds_touching_are_the_same_spell_exact_ones_are_not():
    since_june = ValidTime(d(2025, 6), d(2025, 7))
    stopped_july = ValidTime(to_earliest=d(2025, 7), to_latest=d(2025, 8))
    assert same_spell(stopped_july, since_june, "after")      # started before 1 July, ended in July
    exact_end = ValidTime(d(2020), d(2020), d(2021), d(2021))
    exact_next = ValidTime(d(2021), d(2021), to_earliest=d(2022))
    assert not same_spell(exact_end, exact_next, "after")     # back to back: two spells


def test_start_and_end_from_two_claims_are_assembled_and_labelled():
    result = evaluate([claim("joined", JOINED_JAN), claim("left", LEFT_MAY)], d(2025, 3, 15), anything_recorded=True)
    assert result.answer is Answer.TRUE and result.assembled == (("joined", "left"),)
    assert "one continuous period" in result.notes[0]


def test_no_assembly_outside_the_bounds_or_against_a_counted_false():
    assert evaluate([claim("joined", JOINED_JAN), claim("left", LEFT_MAY)], d(2025, 1, 15), True).answer is Answer.UNKNOWN
    assert evaluate([claim("joined", JOINED_JAN), claim("left", LEFT_MAY)], d(2025, 7, 1), True).answer is Answer.FALSE
    only_start = evaluate([claim("joined", JOINED_JAN)], d(2025, 3, 15), True)
    assert only_start.answer is Answer.UNKNOWN and only_start.assembled == ()


def test_bounding_claims_can_only_say_false():
    cto_since_march = ValidTime(d(2025, 3), d(2025, 4), to_earliest=d(2025, 8, 20))
    left = claim("left", LEFT_MAY)
    assert evaluate([claim("cto", cto_since_march)], d(2025, 7, 15), True, bounding=[left]).answer is Answer.CONTESTED
    assert evaluate([claim("cto", cto_since_march)], d(2025, 4, 15), True, bounding=[left]).answer is Answer.TRUE
