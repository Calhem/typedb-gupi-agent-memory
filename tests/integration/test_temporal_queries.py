"""False, unknown and not-yet-known stay distinct across valid time and transaction time."""

import pytest
from helpers import CHAT, HR, claim, month, observe, record, reports, utc

from gupi.temporal import Answer, ValidTime

pytestmark = pytest.mark.integration

ROLES = {"report": "p:alice", "manager": "p:bob"}
JOB = {"employee": "p:alice", "employer": "o:acme"}


def ask(memory, at, believed_at=None, roles=ROLES, claim_type="reporting"):
    return memory.ask(claim_type, roles, utc(at), believed_at=utc(believed_at) if believed_at else None).answer


def accept_all(memory, *claims):
    for c in claims:
        memory.review(c.id, "accepted", "test")


def test_not_yet_known_then_false(memory, clock):
    """A fact learnt in November: in March nothing was known; now it is known to be false for August."""
    obs = observe(HR, "hr-1", "Alice reported to Bob from March 2024 to June 2025.", "2025-11-01")
    c = reports(obs, valid=ValidTime(*month("2024-03"), *month("2025-06")), valid_to_basis="stated")
    clock.set("2025-11-02")
    record(memory, [obs], [c])
    accept_all(memory, c)

    assert ask(memory, "2025-08", believed_at="2025-03-15") is Answer.NOT_YET_KNOWN
    assert ask(memory, "2025-08", believed_at="2025-11-03") is Answer.FALSE
    assert ask(memory, "2025-01", believed_at="2025-11-03") is Answer.TRUE
    # Recorded but not yet reviewed (between ingestion and acceptance there is no gap here, so use a
    # second proposition that is never accepted): recorded, not believed -> UNKNOWN, never FALSE.
    other = reports(obs, manager="p:sam-lee")
    record(memory, [obs], [other])
    assert ask(memory, "2025-01", roles={"report": "p:alice", "manager": "p:sam-lee"}) is Answer.UNKNOWN
    # Nothing at all about a proposition is NOT_YET_KNOWN, not FALSE.
    assert ask(memory, "2025-01", roles={"report": "p:bob", "manager": "p:alice"}) is Answer.NOT_YET_KNOWN


def test_uncertain_boundaries(memory, clock):
    """Month-precision start and end: certain outside the windows, UNKNOWN inside them."""
    obs = observe(HR, "hr-2", "Alice was at Acme from June 2024 until some time in March 2025.", "2025-04-01")
    c = claim("employment", JOB, obs, ValidTime(*month("2024-06"), *month("2025-03")),
              time_precision="month", valid_to_basis="stated")
    clock.set("2025-04-02")
    record(memory, [obs], [c])
    accept_all(memory, c)

    expected = {"2024-05-31": Answer.FALSE, "2024-06-15": Answer.UNKNOWN, "2024-07-01": Answer.TRUE,
                "2025-02-28": Answer.TRUE, "2025-03-15": Answer.UNKNOWN, "2025-04-01": Answer.FALSE}
    for at, answer in expected.items():
        assert ask(memory, at, roles=JOB, claim_type="employment") is answer, at


def test_year_precision_and_unknown_start(memory, clock):
    year = observe(HR, "hr-3", "Alice joined Acme in 2023 and is still there.", "2025-02-01")
    no_start = observe(CHAT, "msg-1", "Alice left Acme in May 2025.", "2025-06-01")
    joined = claim("employment", JOB, year,
                   ValidTime(utc("2023-01-01"), utc("2024-01-01"), to_earliest=utc("2025-02-01")),
                   time_precision="year", valid_to_basis="ongoing-at-observation")
    left = claim("employment", JOB, no_start, ValidTime(to_earliest=month("2025-05")[0], to_latest=month("2025-05")[1]),
                 valid_to_basis="stated")
    clock.set("2025-06-02")
    record(memory, [year, no_start], [joined, left])
    accept_all(memory, joined, left)

    assert ask(memory, "2023-06", roles=JOB, claim_type="employment") is Answer.UNKNOWN  # within 2023
    assert ask(memory, "2024-06", roles=JOB, claim_type="employment") is Answer.TRUE
    # The departure claim says FALSE after May; the 'still there in February' claim says nothing after
    # February, so this is FALSE rather than CONTESTED.
    assert ask(memory, "2025-07", roles=JOB, claim_type="employment") is Answer.FALSE


def test_retrospective_correction_of_a_start_date(memory, clock):
    first = observe(HR, "hr-4", "Alice reports to Bob from June 2025.", "2025-06-20")
    fix = observe(HR, "hr-5", "Correction: she has reported to Bob since 10 March 2025.", "2025-09-01")
    june = reports(first, valid=ValidTime(*month("2025-06"), to_earliest=utc("2025-06-20")),
                   valid_to_basis="ongoing-at-observation")
    march = reports(fix, valid=ValidTime(utc("2025-03-10"), utc("2025-03-10"), to_earliest=utc("2025-09-01")),
                    valid_to_basis="ongoing-at-observation")
    clock.set("2025-06-21")
    record(memory, [first], [june])
    accept_all(memory, june)
    clock.set("2025-09-02")
    record(memory, [fix], [march])
    accept_all(memory, march)
    memory.supersede(june.id, march.id, reason="start date corrected")

    assert ask(memory, "2025-04", believed_at="2025-07-01") is Answer.FALSE   # what we believed then
    assert ask(memory, "2025-04") is Answer.TRUE                              # what we believe now
    assert ask(memory, "2025-04", believed_at="2025-03-01") is Answer.NOT_YET_KNOWN


def test_late_retraction_without_replacement(memory, clock):
    obs = observe(CHAT, "msg-2", "Alice has reported to Bob since 1 April.", "2025-05-01")
    c = reports(obs, valid=ValidTime(utc("2025-04-01"), utc("2025-04-01"), to_earliest=utc("2025-05-01")),
                valid_to_basis="ongoing-at-observation")
    clock.set("2025-05-02")
    record(memory, [obs], [c])
    accept_all(memory, c)
    clock.set("2025-08-01")
    memory.review(c.id, "retracted", "chat-author", reason="message was a joke")

    assert ask(memory, "2025-04-30", believed_at="2025-06-01") is Answer.TRUE
    # Retraction removes the belief, not the record: recorded but not believed is UNKNOWN, never FALSE.
    assert ask(memory, "2025-04-30") is Answer.UNKNOWN
    assert [r.verdict for r in memory.claim(c.id).reviews] == ["accepted", "retracted"]
