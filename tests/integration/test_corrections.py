"""Reversible corrections and out-of-order updates, on the live server."""

import pytest
from helpers import HR, CHAT, month, observe, record, reports, utc

from gupi.status import Status
from gupi.temporal import Answer, ValidTime

pytestmark = pytest.mark.integration

ROLES = {"report": "p:alice", "manager": "p:bob"}


def accept(memory, *claims):
    memory.review_many([(c.id, "accepted") for c in claims], "reviewer")


def test_a_correction_can_be_withdrawn_and_reinstated(memory, clock):
    first = observe(HR, "hr-1", "Alice has reported to Bob since 2024.", "2025-01-10")
    fix = observe(HR, "hr-2", "Correction: Alice stopped reporting to Bob in June 2025.", "2025-09-01")
    a = reports(first, valid=ValidTime(utc("2024-01-01"), utc("2025-01-01"), to_earliest=utc("2025-01-10")))
    b = reports(fix, valid=ValidTime(*month("2025-06"), *month("2025-06")))
    clock.set("2025-09-02")
    record(memory, [first, fix], [a, b])
    accept(memory, a, b)
    clock.set("2025-09-03")
    sup = memory.supersede(a.id, b.id, reason="HR correction")
    clock.set("2025-10-01")
    memory.withdraw_supersession(sup, "reviewer", reason="the correction was about another Alice")
    clock.set("2025-11-01")
    assert memory.supersede(a.id, b.id, reason="checked again", decided_by="reviewer") == sup  # reinstated

    expected = {"2025-09-02T12:00": {a.id, b.id}, "2025-09-15": {b.id},
                "2025-10-15": {a.id, b.id}, "2025-11-15": {b.id}}
    view = memory.claim(a.id)
    for when, believed in expected.items():
        t = utc(when)
        assert memory.believed_ids(t) == believed, when                      # TypeDB's believed_at ...
        assert (view.status_at(t) is Status.ACCEPTED) == (a.id in believed)  # ... agrees with Python
    assert [r.verdict for r in view.supersessions[0].reviews] == ["retracted", "accepted"]


def test_withdrawing_needs_a_reviewer_and_an_existing_supersession(memory):
    with pytest.raises(ValueError):
        memory.withdraw_supersession("x", "")
    with pytest.raises(KeyError):
        memory.withdraw_supersession("supersession:missing", "reviewer")


def test_a_correction_that_arrives_before_the_original(memory, clock):
    """GUPI receives the September correction first and the February original later."""
    fix = observe(HR, "hr-3", "Correction: Alice stopped reporting to Bob in April 2025.", "2025-09-15")
    original = observe(HR, "hr-4", "Alice has reported to Bob since 2023.", "2025-02-01")
    b = reports(fix, valid=ValidTime(to_earliest=month("2025-04")[0], to_latest=month("2025-04")[1]), valid_to_basis="stated")
    a = reports(original, valid=ValidTime(utc("2023-01-01"), utc("2024-01-01"), to_earliest=utc("2025-02-01")),
                valid_to_basis="ongoing-at-observation")
    clock.set("2025-09-16")
    record(memory, [fix], [b])
    accept(memory, b)
    clock.set("2025-09-20")
    record(memory, [original], [a])
    accept(memory, a)

    # Valid time does not depend on arrival order.
    assert memory.ask("reporting", ROLES, utc("2024-06-01")).answer is Answer.TRUE
    assert memory.ask("reporting", ROLES, utc("2025-08-01")).answer is Answer.FALSE
    assert memory.ask("reporting", ROLES, utc("2024-06-01"), believed_at=utc("2025-09-17")).answer is Answer.UNKNOWN
    # The suggestion orders by when the source said it, not by when GUPI received it.
    (s,) = memory.suggest_supersessions()
    assert (s["old"], s["new"]) == (a.id, b.id) and "arrived after it" in s["reason"]
    assert memory.claim(a.id).supersessions == ()  # only suggested, never applied


def test_old_claims_arriving_late_fill_in_the_past_without_rewriting_history(memory, clock):
    now_obs = observe(CHAT, "c-1", "Alice reports to Bob now.", "2025-06-01")
    past_obs = observe(CHAT, "c-2", "Back in 2022 Alice reported to Bob for the whole year.", "2025-06-01")
    present = reports(now_obs, valid=ValidTime(to_earliest=utc("2025-06-01")), valid_to_basis="ongoing-at-observation")
    past = reports(past_obs, valid=ValidTime(utc("2022-01-01"), utc("2022-01-01"), utc("2023-01-01"), utc("2023-01-01")),
                   valid_to_basis="stated")
    clock.set("2025-06-02")
    record(memory, [now_obs], [present])
    accept(memory, present)
    clock.set("2025-08-01")
    record(memory, [past_obs], [past])
    accept(memory, past)

    assert memory.ask("reporting", ROLES, utc("2022-06-01"), believed_at=utc("2025-07-01")).answer is Answer.UNKNOWN
    assert memory.ask("reporting", ROLES, utc("2022-06-01")).answer is Answer.TRUE
    assert memory.ask("reporting", ROLES, utc("2025-05-01")).answer is Answer.UNKNOWN  # still unknown: start never said
    assert memory.suggest_supersessions() == []  # same observation time: nothing to order
