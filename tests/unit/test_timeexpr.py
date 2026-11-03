from datetime import datetime, timezone

import pytest

from gupi.timeexpr import coarsest, direction, read

OBS = datetime(2025, 11, 14, 16, 30, tzinfo=timezone.utc)  # a Friday


def d(y, m, day=1):
    return datetime(y, m, day, tzinfo=timezone.utc)


@pytest.mark.parametrize("text, earliest, latest, precision", [
    ("2025-03-10", d(2025, 3, 10), d(2025, 3, 11), "day"),
    ("on 10 March 2025", d(2025, 3, 10), d(2025, 3, 11), "day"),
    ("March 10th, 2025", d(2025, 3, 10), d(2025, 3, 11), "day"),
    ("in June 2025", d(2025, 6), d(2025, 7), "month"),
    ("since Dec 2024", d(2024, 12), d(2025, 1), "month"),
    ("2025-06", d(2025, 6), d(2025, 7), "month"),
    ("since 2023", d(2023, 1), d(2024, 1), "year"),
    ("yesterday", d(2025, 11, 13), d(2025, 11, 14), "day"),
    ("today", d(2025, 11, 14), d(2025, 11, 15), "day"),
    ("last week", d(2025, 11, 3), d(2025, 11, 10), "day"),
    ("last month", d(2025, 10), d(2025, 11), "month"),
    ("this year", d(2025, 1), d(2026, 1), "year"),
    ("last year", d(2024, 1), d(2025, 1), "year"),
])
def test_recognised_expressions(text, earliest, latest, precision):
    r = read(text, OBS)
    assert (r.earliest, r.latest, r.precision, r.assumption) == (earliest, latest, precision, None)


def test_month_without_year_needs_a_direction():
    # Past: the most recent such month (the behaviour before this fix, now only when asked for).
    r = read("in June", OBS, "past")
    assert (r.earliest, r.latest) == (d(2025, 6), d(2025, 7)) and "past tense" in r.assumption
    assert read("December", OBS, "past").earliest == d(2024, 12)  # Dec 2025 has not happened by 14 Nov 2025
    assert read("10 March", OBS, "past").earliest == d(2025, 3, 10)
    # Future: the next such month.
    assert read("in June", OBS, "future").earliest == d(2026, 6)
    assert read("December", OBS, "future").earliest == d(2025, 12)
    # No direction: not guessed, except the observation's own month.
    assert read("in June", OBS) is None and read("10 March", OBS) is None
    assert read("in November", OBS).earliest == d(2025, 11)
    # A stated year never needs a direction.
    assert read("June 2025", OBS).earliest == d(2025, 6)


@pytest.mark.parametrize("text", ["", "soon", "a while ago", "early 2024", "Q3", "31 February 2025",
                                  "2025-13", "in the spring", "next year", "3000"])
def test_anything_unrecognised_is_unknown_not_guessed(text):
    assert read(text, OBS) is None


def test_no_observation_date_means_no_relative_reading():
    assert read("yesterday", None) is None


def test_coarsest_precision():
    assert coarsest("day", "year", None) == "year"
    assert coarsest(None) is None


@pytest.mark.parametrize("text, phrase, expected", [
    # past events
    ("The meeting happened in June.", "in June", "past"),
    ("Sam joined Acme in September.", "in September", "past"),
    ("Lena stopped reporting to Raj in June.", "in June", "past"),
    ("The offsite in June was a success.", "in June", "past"),
    ("We met them two years ago, in March.", "in March", "past"),
    ("Ana left Orbit in December.", "in December", "past"),
    ("She became CFO in May.", "in May", "past"),
    # future deadlines and plans
    ("The migration report is due in June.", "in June", "future"),
    ("We will launch in March.", "in March", "future"),
    ("The review is scheduled for 10 March.", "10 March", "future"),
    ("Cutover has been postponed to June.", "June", "future"),
    ("The deadline is 30 April.", "30 April", "future"),
    # the nearest cue wins
    ("Last week we decided the launch will be in June.", "in June", "future"),
    # ambiguous: no tense or scheduling evidence
    ("Budget review: June.", "June", None),
    ("Agenda item - the June numbers", "June", None),
    ("We need the June figures.", "June", None),
    # mixed signals: a plan stated in the past tense may be about a date already gone
    ("We had planned to finish in June.", "in June", None),
    ("The launch was expected in March.", "in March", None),
])
def test_direction_from_the_sentence(text, phrase, expected):
    assert direction(text, text.index(phrase)) == expected


def test_year_boundaries():
    jan = datetime(2026, 1, 10, tzinfo=timezone.utc)
    dec = datetime(2025, 12, 20, tzinfo=timezone.utc)
    left, due = "Ana left in December.", "The audit is due in January."
    assert read("in December", jan, direction(left, left.index("in December"))).earliest == d(2025, 12)
    assert read("in January", dec, direction(due, due.index("in January"))).earliest == d(2026, 1)


def test_phase5_evidence_windows_keep_their_frozen_past_rule():
    """Phase 5's frozen configuration resolved a month without a year to the past; it must stay reproducible."""
    from gupi.evidence import time_window
    asked = datetime(2023, 3, 1, tzinfo=timezone.utc)
    assert time_window("What did Melanie start in June?", asked) == (d(2022, 6), d(2022, 7))
    assert time_window("What is due in June?", asked) == (d(2022, 6), d(2022, 7))  # legacy, even with "due"


def test_explicit_and_inferred_dates_are_distinguished():
    assert read("June 2025", OBS).explicit and read("2025-03-10", OBS).explicit and read("since 2023", OBS).explicit
    inferred = read("in June", OBS, "past")
    assert not inferred.explicit and "inferred" in inferred.assumption
    assert not read("last month", OBS).explicit and not read("yesterday", OBS).explicit


def test_unresolvable_statements_are_left_unread():
    for text, phrase in (("June looks tight.", "June"), ("We had planned to finish in June.", "in June")):
        assert read(phrase, OBS, direction(text, text.index(phrase))) is None


def test_tense_is_read_at_the_phrase_in_the_original_text():
    """Spacing and line breaks before the phrase must not shift where the tense is read."""
    from types import SimpleNamespace as NS

    from gupi.extraction.contract import _time
    text = "Ana met us; the cutover" + " " * 30 + "report is due in June."  # "met" is past, "due" is nearest
    notes, readings = [], []
    vt, _, _ = _time({"end": "in June"}, text, OBS, notes, readings)
    assert vt.to_earliest == d(2026, 6)  # "due": the coming June, not last June
    assert readings[0]["explicit"] is False
