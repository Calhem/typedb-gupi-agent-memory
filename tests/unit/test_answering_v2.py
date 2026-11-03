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


# Q9: start statements about the same period that disagree, each judged on its own (spec §1.3)
JAN = c("jan", ValidTime(d(2025, 1), d(2025, 2)))            # "joined in January 2025"
MAR = c("mar", ValidTime(d(2025, 3), d(2025, 4)))            # "joined in March 2025"
STILL = c("still", ValidTime(to_earliest=d(2025, 9)))        # "still works there" on 1 September
DISPUTE = [JAN, MAR, STILL]


def test_two_start_dates_that_both_establish_the_state_give_it_and_disclose_the_dispute():
    r = classify(DISPUTE, d(2025, 6, 15), True)
    assert (r.answer, r.basis.kind, r.basis.claims) == (Answer.PRESUMED, "joined-spell", ("mar", "still"))
    assert "start date is disputed" in r.explanation and "none is preferred" in r.explanation
    direct = c("mar-still", ValidTime(d(2025, 3), d(2025, 4), to_earliest=d(2025, 9)))
    r = classify([JAN, direct], d(2025, 6, 15), True)
    assert (r.answer, r.basis.kind) == (Answer.TRUE, "direct-span") and "start date is disputed" in r.explanation


def test_two_start_dates_that_straddle_the_instant_are_contested():
    assert at(DISPUTE, d(2025, 2, 15)) == (Answer.CONTESTED, "conflict", ("jan", "mar"))


def test_an_imprecise_month_that_may_fall_after_the_instant_gives_unknown():
    r = classify(DISPUTE, d(2025, 3, 15), True)
    assert (r.answer, r.basis.kind, r.basis.claims) == (Answer.UNKNOWN, "window", ("jan", "mar"))
    assert "too imprecise" in r.explanation and "not assumed to lie between" in r.explanation


def test_disputed_starts_never_make_an_earlier_time_false():
    assert at(DISPUTE, d(2024, 12, 15)) == (Answer.UNKNOWN, "no-coverage", ())  # Q1 still holds


def test_neither_start_is_preferred_whatever_the_order():
    for when in (d(2025, 2, 15), d(2025, 3, 15), d(2025, 6, 15)):
        assert at(DISPUTE, when) == at(list(reversed(DISPUTE)), when)


def test_once_a_correction_supersedes_one_start_the_other_stands_alone():
    """The belief cutoff removes a superseded claim before classification (ADR 0006)."""
    assert at([MAR, STILL], d(2025, 2, 15)) == (Answer.UNKNOWN, "no-coverage", ())
    r = classify([MAR, STILL], d(2025, 6, 15), True)
    assert r.answer is Answer.PRESUMED and not r.notes


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
