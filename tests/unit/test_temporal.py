from datetime import datetime, timezone

from gupi.temporal import Truth, ValidTime, holds_at


def d(y, m, day=1):
    return datetime(y, m, day, tzinfo=timezone.utc)


JUNE_END = dict(to_earliest=d(2025, 6), to_latest=d(2025, 7))  # "stopped in June 2025"
SINCE_2024 = dict(from_earliest=d(2024, 1), from_latest=d(2024, 1))  # exact start


def test_exact_interval_is_half_open():
    vt = ValidTime(from_earliest=d(2025, 1), from_latest=d(2025, 1), to_earliest=d(2025, 3), to_latest=d(2025, 3))
    assert holds_at(vt, d(2025, 1)) is Truth.TRUE
    assert holds_at(vt, d(2025, 3)) is Truth.FALSE
    assert holds_at(vt, d(2024, 12, 31)) is Truth.FALSE


def test_month_precision_end_is_uncertain_inside_the_month():
    vt = ValidTime(**SINCE_2024, **JUNE_END)
    assert holds_at(vt, d(2025, 5, 31)) is Truth.TRUE
    assert holds_at(vt, d(2025, 6, 15)) is Truth.UNKNOWN
    assert holds_at(vt, d(2025, 7)) is Truth.FALSE


def test_missing_end_is_unknown_not_ongoing():
    assert holds_at(ValidTime(**SINCE_2024), d(2030, 1)) is Truth.UNKNOWN


def test_ongoing_at_observation_is_true_only_up_to_the_observation():
    vt = ValidTime(**SINCE_2024, to_earliest=d(2025, 1, 10))
    assert holds_at(vt, d(2025, 1, 5)) is Truth.TRUE
    assert holds_at(vt, d(2025, 2)) is Truth.UNKNOWN


def test_missing_start_is_unknown_unless_already_ended():
    assert holds_at(ValidTime(**JUNE_END), d(2025, 3)) is Truth.UNKNOWN
    assert holds_at(ValidTime(**JUNE_END), d(2025, 8)) is Truth.FALSE


def test_month_precision_start():
    vt = ValidTime(from_earliest=d(2025, 6), from_latest=d(2025, 7), to_earliest=d(2026, 1))  # CTO from June 2025
    assert holds_at(vt, d(2025, 5)) is Truth.FALSE
    assert holds_at(vt, d(2025, 6, 10)) is Truth.UNKNOWN
    assert holds_at(vt, d(2025, 7, 2)) is Truth.TRUE


def test_combine_keeps_the_answers_apart():
    from gupi.temporal import Answer, combine

    assert combine([], anything_recorded=False) is Answer.NOT_YET_KNOWN
    assert combine([], anything_recorded=True) is Answer.UNKNOWN
    assert combine([Truth.UNKNOWN], anything_recorded=True) is Answer.UNKNOWN
    assert combine([Truth.FALSE, Truth.UNKNOWN], anything_recorded=True) is Answer.FALSE
    assert combine([Truth.TRUE, Truth.UNKNOWN], anything_recorded=True) is Answer.TRUE
    assert combine([Truth.TRUE, Truth.FALSE], anything_recorded=True) is Answer.CONTESTED
