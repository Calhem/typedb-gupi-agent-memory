"""Review queue, batch decisions and decision history on the live server."""

import pytest
from helpers import CHAT, HR, observe, record, reports, utc

from gupi import review
from gupi.status import Status

pytestmark = pytest.mark.integration


@pytest.fixture
def three(memory, clock):
    obs = [observe(HR, "hr-1", "Alice reports to Bob.", "2025-01-05"),
           observe(CHAT, "c-1", "Alice reports to Sam Lee.", "2025-01-06"),
           observe(CHAT, "c-2", "Alice reports to Sam Roe.", "2025-01-07")]
    claims = [reports(obs[0]), reports(obs[1], manager="p:sam-lee"), reports(obs[2], manager="p:sam-roe")]
    clock.set("2025-01-10")
    record(memory, obs[:1], claims[:1])
    clock.set("2025-01-11")
    record(memory, obs[1:], claims[1:])
    return claims


def test_queue_lists_hypotheses_oldest_first_and_shrinks_as_decisions_are_made(memory, clock, three):
    clock.set("2025-01-12")
    queued = [i.claim.id for i in memory.review_queue()]
    assert queued[0] == three[0].id and set(queued[1:]) == {three[1].id, three[2].id}  # same batch: ordered by id
    memory.review_many([(three[0].id, "accepted"), (three[1].id, "rejected")], "reviewer", reason="checked HR")
    assert [i.claim.id for i in memory.review_queue()] == [three[2].id]
    # The queue as it was before the decisions is still reconstructible.
    assert len(memory.review_queue(at=utc("2025-01-11T12:00"))) == 3
    assert len(memory.review_queue(claim_type="employment")) == 0


def test_batch_decisions_are_all_or_nothing(memory, clock, three):
    clock.set("2025-01-12")
    with pytest.raises(KeyError):
        memory.review_many([(three[0].id, "accepted"), ("claim:missing", "accepted")], "reviewer")
    assert memory.claim(three[0].id).reviews == ()
    with pytest.raises(ValueError, match="once per batch"):
        memory.review_many([(three[0].id, "accepted"), (three[0].id, "rejected")], "reviewer")
    with pytest.raises(ValueError, match="decided_by"):
        memory.review_many([(three[0].id, "accepted")], "")


def test_history_reads_as_a_timeline(memory, clock, three):
    for when, verdict in (("2025-02-01", "accepted"), ("2025-05-01", "rejected"), ("2025-07-01", "accepted")):
        clock.set(when)
        memory.review(three[0].id, verdict, "reviewer", reason=f"{verdict} on review")
    events = review.history(memory.claim(three[0].id))
    assert [e.kind for e in events] == ["recorded", "accepted", "rejected", "accepted"]
    assert events[2].detail == "rejected by reviewer: rejected on review"
    assert memory.claim(three[0].id).status_at(utc("2025-06-01")) is Status.REJECTED
