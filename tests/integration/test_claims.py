"""ADR-0001 review scenarios and review history, on the live server.

Each claim is one attestation with its own id and evidence, so every claim and its provenance can be
identified and retrieved on its own, even when several claims are about the same proposition.
"""

import pytest
from helpers import CHAT, HR, WIKI, month, observe, record, reports, claim, utc

from gupi.status import Status
from gupi.temporal import Answer, ValidTime

pytestmark = pytest.mark.integration

SINCE_MARCH_2024 = dict(zip(("from_earliest", "from_latest"), month("2024-03")))


def test_independent_sources_asserting_the_same_fact(memory, clock):
    hr = observe(HR, "hr-1", "Alice reports to Bob.", "2025-01-05")
    wiki = observe(WIKI, "wiki-7", "Alice's manager: Bob", "2025-01-06")
    a, b = (reports(o, valid=ValidTime(**SINCE_MARCH_2024, to_earliest=o.observed_at),
                    valid_to_basis="ongoing-at-observation") for o in (hr, wiki))
    clock.set("2025-01-10")
    record(memory, [hr, wiki], [a, b])
    for c in (a, b):
        memory.review(c.id, "accepted", "test")

    assert a.id != b.id and a.proposition_key == b.proposition_key
    by_id = {c.id: c for c in memory.claims_about("p:alice")}
    assert set(by_id) == {a.id, b.id}
    assert [(e.source_id, e.quote) for e in by_id[a.id].evidence] == [("src:hr", "Alice reports to Bob.")]
    assert [(e.source_id, e.quote) for e in by_id[b.id].evidence] == [("src:wiki", "Alice's manager: Bob")]

    # Retracting one attestation leaves the other standing.
    clock.set("2025-02-01")
    memory.review(a.id, "retracted", "hr", reason="entered against the wrong person")
    now = memory.ask("reporting", {"report": "p:alice", "manager": "p:bob"}, utc("2025-01-01"))
    assert now.answer is Answer.TRUE and [c.id for c, _ in now.believed] == [b.id]
    before = memory.ask("reporting", {"report": "p:alice", "manager": "p:bob"}, utc("2025-01-01"),
                        believed_at=utc("2025-01-15"))
    assert {c.id for c, _ in before.believed} == {a.id, b.id}


def test_contradictory_claims_are_kept_side_by_side(memory, clock):
    roles = {"employee": "p:alice", "employer": "o:acme"}
    hr = observe(HR, "hr-2", "Alice joined Acme as CTO in June 2025.", "2025-07-01")
    chat = observe(CHAT, "msg-9", "Alice is our new VP Engineering (since June).", "2025-07-02")
    since_june = ValidTime(*month("2025-06"))
    cto = claim("employment", roles, hr, since_june, values={"job-title": "CTO"})
    vp = claim("employment", roles, chat, since_june, values={"job-title": "VP Engineering"})
    clock.set("2025-07-03")
    record(memory, [hr, chat], [cto, vp])
    for c in (cto, vp):
        memory.review(c.id, "accepted", "test")

    # She was employed; which title is disputed, and both claims are returned with their sources.
    employed = memory.ask("employment", roles, utc("2025-08"))
    assert employed.answer is Answer.UNKNOWN  # the end of employment was never stated
    titles = {c.values["job-title"]: c.evidence[0].source_id for c in employed.considered}
    assert titles == {"CTO": "src:hr", "VP Engineering": "src:chat"}
    assert memory.ask("employment", roles, utc("2025-05"), values={"job-title": "CTO"}).answer is Answer.FALSE


def test_contradictory_time_bounds_are_contested(memory, clock):
    hr = observe(HR, "hr-3", "Alice stopped reporting to Bob in June 2025.", "2025-07-01")
    chat = observe(CHAT, "msg-12", "Alice still reports to Bob.", "2025-09-01")
    ended = reports(hr, valid=ValidTime(*month("2024-03"), *month("2025-06")), valid_to_basis="stated")
    ongoing = reports(chat, valid=ValidTime(*month("2024-03"), to_earliest=utc("2025-09-01")),
                      valid_to_basis="ongoing-at-observation")
    clock.set("2025-09-02")
    record(memory, [hr, chat], [ended, ongoing])
    for c in (ended, ongoing):
        memory.review(c.id, "accepted", "test")

    result = memory.ask("reporting", {"report": "p:alice", "manager": "p:bob"}, utc("2025-08"))
    assert result.answer is Answer.CONTESTED
    assert {c.id: t.value for c, t in result.believed} == {ended.id: "false", ongoing.id: "true"}


def test_retrospective_correction_keeps_history(memory, clock):
    first = observe(HR, "hr-4", "Alice has reported to Bob since March 2024.", "2025-01-10T09:00")
    later = observe(HR, "hr-5", "Correction: Alice stopped reporting to Bob in June.", "2025-11-14")
    original = reports(first, valid=ValidTime(*month("2024-03"), to_earliest=utc("2025-01-10T09:00")),
                       valid_to_basis="ongoing-at-observation", time_precision="month")
    corrected = reports(later, valid=ValidTime(*month("2024-03"), *month("2025-06")), valid_to_basis="stated",
                        time_precision="month")
    clock.set("2025-01-10T09:05")
    record(memory, [first], [original])
    memory.review(original.id, "accepted", "test")
    clock.set("2025-11-15")
    record(memory, [later], [corrected])
    memory.review(corrected.id, "accepted", "test")
    memory.supersede(original.id, corrected.id, reason="late correction")

    roles = {"report": "p:alice", "manager": "p:bob"}
    assert memory.ask("reporting", roles, utc("2025-08")).answer is Answer.FALSE
    assert memory.ask("reporting", roles, utc("2025-08"), believed_at=utc("2025-03-15")).answer is Answer.UNKNOWN
    assert memory.ask("reporting", roles, utc("2025-01-05"), believed_at=utc("2025-03-15")).answer is Answer.TRUE

    old = memory.claim(original.id)  # still there, still traceable
    assert old.status_at(utc("2025-12")) is Status.SUPERSEDED
    assert old.superseded_by == ((corrected.id, utc("2025-11-15")),)
    assert memory.claim(corrected.id).supersedes == (original.id,)
    assert [e.observation_id for e in old.evidence] == [first.id]


def test_multiple_interpretations_of_one_observation(memory, clock):
    chat = observe(CHAT, "msg-20", "Alice now reports to Sam.", "2025-10-01")
    lee = reports(chat, manager="p:sam-lee", method="extractor:fixture")
    roe = reports(chat, manager="p:sam-roe", method="extractor:fixture")
    clock.set("2025-10-02")
    record(memory, [chat], [lee, roe])
    memory.mark_alternatives([lee.id, roe.id], reason='"Sam" is ambiguous')

    a, b = memory.claim(lee.id), memory.claim(roe.id)
    assert a.alternatives == (roe.id,) and b.alternatives == (lee.id,)
    assert a.evidence[0].observation_id == b.evidence[0].observation_id == chat.id
    assert a.status_at(clock()) is Status.HYPOTHESIS
    # Hypotheses are recorded but not believed: the answer is unknown, not false.
    assert memory.ask("reporting", {"report": "p:alice", "manager": "p:sam-lee"}, utc("2025-10-01")).answer \
        is Answer.UNKNOWN

    clock.set("2025-10-05")
    memory.review(lee.id, "accepted", "user")
    memory.review(roe.id, "rejected", "user")
    assert memory.ask("reporting", {"report": "p:alice", "manager": "p:sam-roe"}, utc("2025-10-01")).answer \
        is Answer.UNKNOWN
    assert memory.believed_ids(clock()) == {lee.id}


def test_reviews_are_historical_and_a_rejected_claim_can_be_reaccepted(memory, clock):
    obs = observe(HR, "hr-6", "Alice reports to Bob.", "2025-01-05")
    c = reports(obs)
    clock.set("2025-01-10")
    record(memory, [obs], [c])
    for when, verdict in (("2025-02-01", "accepted"), ("2025-05-01", "rejected"), ("2025-07-01", "accepted")):
        clock.set(when)
        memory.review(c.id, verdict, "reviewer")

    view = memory.claim(c.id)
    assert [r.verdict for r in view.reviews] == ["accepted", "rejected", "accepted"]
    expected = {"2025-01-05": Status.NOT_RECORDED, "2025-01-15": Status.HYPOTHESIS, "2025-03-01": Status.ACCEPTED,
                "2025-06-01": Status.REJECTED, "2025-08-01": Status.ACCEPTED}
    for when, status in expected.items():
        assert view.status_at(utc(when)) is status, when
        # TypeDB's believed_at() and the Python status agree.
        assert (c.id in memory.believed_ids(utc(when))) == (status is Status.ACCEPTED), when


def test_same_timestamp_conflict_is_not_believed(memory, clock):
    obs = observe(HR, "hr-7", "Alice reports to Bob.", "2025-01-05")
    c = reports(obs)
    clock.set("2025-01-10")
    record(memory, [obs], [c])
    memory.review(c.id, "accepted", "reviewer-a")
    memory.review(c.id, "rejected", "reviewer-b")
    assert memory.claim(c.id).status_at(clock()) is Status.REJECTED
    assert memory.believed_ids(clock()) == set()


def test_repeating_a_decision_is_idempotent_and_time_cannot_go_backwards(memory, clock):
    obs = observe(HR, "hr-8", "Alice reports to Bob.", "2025-01-05")
    c = reports(obs)
    clock.set("2025-01-10")
    record(memory, [obs], [c])
    first = memory.review(c.id, "accepted", "reviewer")
    clock.set("2025-01-11")
    assert memory.review(c.id, "accepted", "reviewer") == first
    assert len(memory.claim(c.id).reviews) == 1

    clock.set("2025-01-09")
    with pytest.raises(ValueError, match="backwards"):
        memory.review(c.id, "rejected", "reviewer")
    with pytest.raises(KeyError):
        memory.review("claim:missing", "accepted", "reviewer")
