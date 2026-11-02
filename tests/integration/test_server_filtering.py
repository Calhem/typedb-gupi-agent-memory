"""TypeDB does the filtering: per-claim status functions, bounded comparisons, configurable rules."""

import pytest
from helpers import HR, CHAT, month, observe, record, reports, claim, utc

from gupi import retrieval
from gupi.memory import Memory
from gupi.status import Status
from gupi.temporal import Answer, ValidTime
from gupi.typedb.connection import transaction
from typedb.driver import TransactionType

pytestmark = pytest.mark.integration

JOB = {"employee": "p:alice", "employer": "o:acme"}


@pytest.fixture
def no_full_scans(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("a retrieval path loaded every claim")
    monkeypatch.setattr(retrieval, "all_claims", refuse)


def test_typedb_hypothesis_and_belief_agree_with_python(memory, clock, no_full_scans):
    obs = [observe(HR, f"hr-{i}", f"Alice reports to Bob ({i}).", "2025-01-05") for i in range(3)]
    cs = [reports(o) for o in obs]
    clock.set("2025-01-10")
    record(memory, obs, cs)
    clock.set("2025-02-01")
    memory.review(cs[0].id, "accepted", "r")
    memory.review(cs[1].id, "rejected", "r")
    clock.set("2025-03-01")
    memory.supersede(cs[0].id, cs[2].id)
    for when in ("2025-01-20", "2025-02-15", "2025-03-15"):
        t = utc(when)
        with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
            hyp = set(retrieval.hypothesis_ids(tx, t))
            believed = retrieval.believed_among(tx, [c.id for c in cs], t)
        views = memory.claims([c.id for c in cs])
        assert hyp == {v.id for v in views if v.status_at(t) is Status.HYPOTHESIS}, when
        assert believed == {v.id for v in views if v.status_at(t) is Status.ACCEPTED}, when


def test_joined_and_left_are_assembled_into_one_spell(memory, clock, no_full_scans):
    joined = observe(HR, "hr-9", "Alice joined Acme in January 2025.", "2025-02-01")
    left = observe(HR, "hr-10", "Alice left Acme in May 2025.", "2025-06-01")
    a = claim("employment", JOB, joined, ValidTime(*month("2025-01")))
    b = claim("employment", JOB, left, ValidTime(to_earliest=month("2025-05")[0], to_latest=month("2025-05")[1]))
    clock.set("2025-06-02")
    record(memory, [joined, left], [a, b])
    memory.review_many([(a.id, "accepted"), (b.id, "accepted")], "r")
    result = memory.ask("employment", JOB, utc("2025-03-15"))
    assert result.answer is Answer.TRUE and result.evaluation.assembled == ((a.id, b.id),)
    assert memory.ask("employment", JOB, utc("2025-07-01")).answer is Answer.FALSE


def test_value_question_counts_an_untitled_departure(memory, clock, no_full_scans):
    cto = observe(CHAT, "c-1", "Since March 2025, Alice works at Acme as CTO.", "2025-08-20")
    left = observe(HR, "hr-11", "Alice left Acme in May 2025.", "2025-06-01")
    a = claim("employment", JOB, cto, ValidTime(*month("2025-03"), to_earliest=utc("2025-08-20")), values={"job-title": "CTO"})
    b = claim("employment", JOB, left, ValidTime(to_earliest=month("2025-05")[0], to_latest=month("2025-05")[1]))
    clock.set("2025-08-21")
    record(memory, [cto, left], [a, b])
    memory.review_many([(a.id, "accepted"), (b.id, "accepted")], "r")
    assert memory.ask("employment", JOB, utc("2025-07-15"), values={"job-title": "CTO"}).answer is Answer.CONTESTED
    assert memory.ask("employment", JOB, utc("2025-04-15"), values={"job-title": "CTO"}).answer is Answer.TRUE


def test_queue_and_conflicts_never_scan_everything_and_rules_are_configurable(driver, database, clock, no_full_scans):
    bob = observe(HR, "hr-12", "Alice reports to Bob since March 2025.", "2025-09-01")
    sam = observe(CHAT, "c-2", "Alice has reported to Sam Lee since April 2025.", "2025-09-02")
    c1 = reports(bob, valid=ValidTime(utc("2025-03-01"), utc("2025-03-01"), to_earliest=utc("2025-09-01")))
    c2 = reports(sam, manager="p:sam-lee", valid=ValidTime(utc("2025-04-01"), utc("2025-04-01"), to_earliest=utc("2025-09-02")))
    memory = Memory.open(database, packs=("core", "people"), driver=driver, clock=clock)
    clock.set("2025-09-03")
    record(memory, [bob, sam], [c1, c2])
    memory.review_many([(c1.id, "accepted"), (c2.id, "accepted")], "r")
    assert [x.kind for x in memory.conflicts()] == ["contradiction"]
    relaxed = Memory(driver, database, clock, constraints={"single_valued_attributes": {}, "one_player_at_a_time": {}})
    assert relaxed.conflicts() == []  # a domain where people may have two managers at once
    assert relaxed.review_queue() == []
