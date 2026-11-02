from datetime import datetime, timezone

from gupi.status import ReviewEvent, Status, status_at


def d(m, day=1):
    return datetime(2025, m, day, tzinfo=timezone.utc)


RECORDED = d(1)


def test_no_reviews_is_a_hypothesis_and_before_recording_is_not_recorded():
    assert status_at(RECORDED, [], [], d(2)) is Status.HYPOTHESIS
    assert status_at(RECORDED, [], [], datetime(2024, 12, 31, tzinfo=timezone.utc)) is Status.NOT_RECORDED


def test_latest_review_wins_so_rejection_can_be_reversed():
    reviews = [ReviewEvent("accepted", d(2)), ReviewEvent("rejected", d(5)), ReviewEvent("accepted", d(7))]
    assert status_at(RECORDED, reviews, [], d(3)) is Status.ACCEPTED
    assert status_at(RECORDED, reviews, [], d(6)) is Status.REJECTED
    assert status_at(RECORDED, reviews, [], d(8)) is Status.ACCEPTED


def test_ties_are_conservative_and_supersession_overrides():
    tie = [ReviewEvent("accepted", d(2)), ReviewEvent("retracted", d(2))]
    assert status_at(RECORDED, tie, [], d(3)) is Status.RETRACTED
    assert status_at(RECORDED, [ReviewEvent("accepted", d(2))], [d(4)], d(5)) is Status.SUPERSEDED
    assert status_at(RECORDED, [ReviewEvent("accepted", d(2))], [d(4)], d(3)) is Status.ACCEPTED
