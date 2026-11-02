from datetime import datetime, timezone

import pytest

from gupi.timeexpr import coarsest, read

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


def test_month_without_year_is_the_most_recent_and_says_so():
    r = read("in June", OBS)
    assert (r.earliest, r.latest) == (d(2025, 6), d(2025, 7))
    assert "inferred" in r.assumption
    later = read("December", OBS)  # December 2025 has not happened by 14 Nov 2025
    assert later.earliest == d(2024, 12)
    assert read("10 March", OBS).earliest == d(2025, 3, 10)


@pytest.mark.parametrize("text", ["", "soon", "a while ago", "early 2024", "Q3", "31 February 2025",
                                  "2025-13", "in the spring", "next year", "3000"])
def test_anything_unrecognised_is_unknown_not_guessed(text):
    assert read(text, OBS) is None


def test_no_observation_date_means_no_relative_reading():
    assert read("yesterday", None) is None


def test_coarsest_precision():
    assert coarsest("day", "year", None) == "year"
    assert coarsest(None) is None
