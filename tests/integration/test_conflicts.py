"""Conflict detection and the separate-periods rule, on the live server."""

import pytest
from helpers import CHAT, HR, claim, month, observe, record, reports, utc

from gupi.conflicts import CONTRADICTION, DIFFERING
from gupi.temporal import Answer, ValidTime

pytestmark = pytest.mark.integration

JOB = {"employee": "p:alice", "employer": "o:acme"}


def accept(memory, *claims):
    memory.review_many([(c.id, "accepted") for c in claims], "reviewer")


def test_contradiction_and_differing_evidence_are_reported_separately(memory, clock):
    hr = observe(HR, "hr-1", "Alice is the CTO of Acme since June.", "2025-10-01")
    chat = observe(CHAT, "c-1", "Alice is VP Engineering at Acme since June.", "2025-10-02")
    old = observe(HR, "hr-2", "Alice was a Senior Engineer at Acme.", "2025-02-01")
    since_june = lambda o: ValidTime(*month("2025-06"), to_earliest=o.observed_at)
    cto = claim("employment", JOB, hr, since_june(hr), values={"job-title": "CTO"})
    vp = claim("employment", JOB, chat, since_june(chat), values={"job-title": "VP Engineering"})
    senior = claim("employment", JOB, old, ValidTime(to_earliest=old.observed_at), values={"job-title": "Senior Engineer"})
    clock.set("2025-10-03")
    record(memory, [hr, chat, old], [cto, vp, senior])
    accept(memory, cto, vp, senior)

    found = {(x.kind, x.claim_ids) for x in memory.conflicts()}
    assert (CONTRADICTION, tuple(sorted((cto.id, vp.id)))) in found
    assert (DIFFERING, tuple(sorted((senior.id, cto.id)))) in found  # earlier title: possibly a promotion


def test_separate_periods_are_not_contested(memory, clock):
    first = observe(HR, "hr-3", "Alice reported to Bob from 2020 to 2021.", "2025-01-01")
    second = observe(HR, "hr-4", "Alice has reported to Bob since 2024.", "2025-01-02")
    a = reports(first, valid=ValidTime(utc("2020-01-01"), utc("2021-01-01"), utc("2021-01-01"), utc("2022-01-01")))
    b = reports(second, valid=ValidTime(utc("2024-01-01"), utc("2025-01-01"), to_earliest=second.observed_at))
    clock.set("2025-01-03")
    record(memory, [first, second], [a, b])
    accept(memory, a, b)
    roles = {"report": "p:alice", "manager": "p:bob"}
    assert memory.ask("reporting", roles, utc("2021-01-01")).answer is Answer.UNKNOWN  # end month of spell one
    assert memory.ask("reporting", roles, utc("2020-06-01")).answer is Answer.UNKNOWN  # start year unknown in detail
    assert memory.ask("reporting", roles, utc("2023-06-01")).answer is Answer.FALSE    # between the spells
    assert memory.conflicts() == []


def test_queue_shows_what_a_hypothesis_would_contradict(memory, clock):
    believed_obs = observe(HR, "hr-5", "Alice reports to Bob, since March 2025.", "2025-09-01")
    new_obs = observe(CHAT, "c-2", "Alice has reported to Sam Lee since April 2025.", "2025-09-02")
    bob = reports(believed_obs, valid=ValidTime(utc("2025-03-01"), utc("2025-03-01"), to_earliest=utc("2025-09-01")))
    sam = reports(new_obs, manager="p:sam-lee",
                  valid=ValidTime(utc("2025-04-01"), utc("2025-04-01"), to_earliest=utc("2025-09-02")))
    clock.set("2025-09-03")
    record(memory, [believed_obs, new_obs], [bob, sam])
    accept(memory, bob)
    (item,) = memory.review_queue()
    assert item.claim.id == sam.id
    assert [c.kind for c in item.conflicts] == [CONTRADICTION] and "two different managers" in item.conflicts[0].reason
