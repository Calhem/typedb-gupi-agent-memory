"""Answer semantics v2 beyond truth-table rows R1-R23 (tests/acceptance): the decisions and edges they do not
pin down (docs/specialist/v2-truth-semantics.md §1, §5)."""

from datetime import datetime, timezone
from types import SimpleNamespace as NS

from gupi.answering_v2 import classify
from gupi.temporal import Answer, ValidTime


def d(y, m=1, day=1):
    return datetime(y, m, day, tzinfo=timezone.utc)


def c(cid, vt, polarity="positive"):
    return NS(id=cid, valid=vt, polarity=polarity)


JOINED = c("joined", ValidTime(d(2024, 1), d(2024, 2)))
LEFT_MAR = c("left-mar", ValidTime(to_earliest=d(2024, 3), to_latest=d(2024, 4)))
LEFT_MAY = c("left-may", ValidTime(to_earliest=d(2024, 5), to_latest=d(2024, 6)))
STILL_SEP = c("still-sep", ValidTime(to_earliest=d(2024, 9)))


def at(claims, when, **kw):
    r = classify(claims, when, True, **kw)
    return r.answer, r.basis.kind, r.basis.claims


def test_competing_end_statements_are_contested_between_them_q2():
    claims = [JOINED, LEFT_MAR, LEFT_MAY]
    assert at(claims, d(2024, 4, 15)) == (Answer.CONTESTED, "conflict", ("left-mar", "left-may"))
    assert at(claims, d(2024, 3, 15)) == (Answer.UNKNOWN, "window", ("left-mar",))
    assert at(claims, d(2024, 6, 15)) == (Answer.FALSE, "termination-continuing", ("left-may",))


def test_competing_start_statements_use_the_provisional_q9_rule_and_say_so():
    joined_mar = c("joined-mar", ValidTime(d(2024, 3), d(2024, 4)))
    claims = [JOINED, joined_mar, STILL_SEP]
    r = classify(claims, d(2024, 2, 15), True)
    assert (r.answer, r.basis.kind) == (Answer.UNKNOWN, "window")
    assert "Q9, provisional rule" in r.explanation and r.notes
    assert at(claims, d(2024, 5)) == (Answer.PRESUMED, "joined-spell", ("joined", "joined-mar", "still-sep"))


def test_bounding_claims_only_contribute_negative_evidence():
    cto = c("cto", ValidTime(d(2025, 3), d(2025, 4), to_earliest=d(2025, 8, 20)))
    left = c("left", ValidTime(to_earliest=d(2025, 5), to_latest=d(2025, 6)))
    employed = c("employed", ValidTime(d(2020), d(2021), to_earliest=d(2030)))
    assert at([cto], d(2025, 7, 15), bounding=[left])[0] is Answer.CONTESTED
    assert at([cto], d(2025, 4, 15), bounding=[left])[0] is Answer.TRUE
    assert at([], d(2025, 1), bounding=[employed])[0] is Answer.UNKNOWN  # never TRUE from a bounding claim


def test_exact_bounds_are_half_open():
    exact = c("exact", ValidTime(d(2020), d(2020), d(2021), d(2021)))
    assert at([exact], d(2020, 6))[0] is Answer.TRUE
    assert at([exact], d(2021))[:2] == (Answer.FALSE, "termination-continuing")


def test_missing_evidence_is_never_false():
    assert at([JOINED], d(2030)) == (Answer.UNKNOWN, "no-coverage", ())
    assert at([STILL_SEP], d(2030)) == (Answer.UNKNOWN, "no-coverage", ())
    assert at([STILL_SEP], d(2020)) == (Answer.UNKNOWN, "no-coverage", ())


def test_a_negation_is_not_a_termination():
    """A negation covers only its own time and neither ends nor blocks a joined period (spec §1.4)."""
    negation = c("neg-jul", ValidTime(to_earliest=d(2024, 7)), "negative")
    claims = [JOINED, negation, STILL_SEP]
    assert at(claims, d(2024, 7)) == (Answer.FALSE, "negation", ("neg-jul",))
    assert at(claims, d(2024, 8))[0] is Answer.PRESUMED


def test_explanations_state_what_the_answer_rests_on():
    r = classify([JOINED, LEFT_MAR], d(2024, 7), True)
    assert "default, not an observation" in r.explanation and "left-mar" in r.explanation
    r = classify([JOINED, STILL_SEP], d(2024, 5), True)
    assert "assumes no unrecorded break" in r.explanation
    assert classify([], d(2024), False).basis.kind == "not-recorded"
