"""Structured questions: citations, exclusions with reasons, open roles, names and as-of answers.

These scenarios are separate from the frozen retrieval benchmark (tests/fixtures/retrieval)."""

import pytest
from helpers import CHAT, HR, observe, record, reports, utc

from gupi import retrieval
from gupi.query import Question
from gupi.records import Batch, Referent
from gupi.temporal import Answer, ValidTime

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def no_full_scans(monkeypatch):
    monkeypatch.setattr(retrieval, "all_claims", lambda *a, **k: (_ for _ in ()).throw(AssertionError("full scan")))


@pytest.fixture
def world(memory, clock):
    bob = observe(HR, "hr-1", "Alice has reported to Bob since 2024.", "2025-02-01")
    sam = observe(CHAT, "c-1", "Alice reports to Sam Lee.", "2025-03-01")
    roe = observe(CHAT, "c-2", "Alice reports to Sam Roe.", "2025-03-02")
    later = observe(HR, "hr-2", "Alice stopped reporting to Bob in June 2025.", "2025-09-01")
    c_bob = reports(bob, valid=ValidTime(utc("2024-01-01"), utc("2025-01-01"), to_earliest=utc("2025-02-01")))
    c_sam = reports(sam, manager="p:sam-lee", valid=ValidTime(to_earliest=utc("2025-03-01")))
    c_roe = reports(roe, manager="p:sam-roe", valid=ValidTime(to_earliest=utc("2025-03-02")))
    c_end = reports(later, valid=ValidTime(to_earliest=utc("2025-06-01"), to_latest=utc("2025-07-01")))
    clock.set("2025-03-05")
    record(memory, [bob, sam, roe], [c_bob, c_sam, c_roe])
    memory.review_many([(c_bob.id, "accepted"), (c_sam.id, "rejected")], "reviewer", reason="checked")
    clock.set("2025-09-02")
    record(memory, [later], [c_end])
    memory.review(c_end.id, "accepted", "reviewer")
    return {"bob": c_bob, "sam": c_sam, "roe": c_roe, "end": c_end}


def test_closed_question_cites_evidence_and_explains_exclusions(memory, world):
    r = memory.query(Question("reporting", {"report": "p:alice", "manager": "p:bob"}, utc("2025-01-15")))
    assert r.answer is Answer.TRUE
    (cite,) = r.citations
    assert (cite.quote, cite.source_id, cite.said_at, cite.verdict) == (
        "Alice has reported to Bob since 2024.", "src:hr", utc("2025-02-01"), "true")
    assert r.temporal["believed_at"] == utc("2025-09-02") and r.steps
    assert memory.query(Question("reporting", {"report": "p:alice", "manager": "p:bob"}, utc("2025-08-01"))).answer is Answer.FALSE


def test_rejected_and_unreviewed_claims_are_not_evidence(memory, world):
    rejected = memory.query(Question("reporting", {"report": "p:alice", "manager": "p:sam-lee"}, utc("2025-02-15")))
    assert rejected.answer is Answer.UNKNOWN and rejected.citations == []
    assert rejected.excluded == [(world["sam"].id, "rejected by reviewer on 2025-03-05: checked")]
    hypothesis = memory.query(Question("reporting", {"report": "p:alice", "manager": "p:sam-roe"}, utc("2025-02-15")))
    assert hypothesis.answer is Answer.UNKNOWN and hypothesis.excluded == [(world["roe"].id, "an unreviewed hypothesis")]


def test_open_role_and_as_of(memory, world):
    r = memory.query(Question("reporting", {"report": "p:alice", "manager": None}, utc("2025-01-15")))
    assert r.answer is Answer.TRUE and r.binding == ["Bob"]
    assert {b.label: b.answer for b in r.bindings} == {"Bob": Answer.TRUE, "Sam Lee": Answer.UNKNOWN, "Sam Roe": Answer.UNKNOWN}
    then = memory.query(Question("reporting", {"report": "p:alice", "manager": "p:bob"}, utc("2025-08-01"),
                                 believed_at=utc("2025-04-01")))
    assert then.answer is Answer.UNKNOWN
    assert (world["end"].id, "recorded 2025-09-02, after the belief time") in then.excluded


def test_names_unknown_and_ambiguous(memory, world):
    assert memory.query_by_name("reporting", {"report": "Alice", "manager": "Bob"}, utc("2025-01-15")).answer is Answer.TRUE
    nobody = memory.query_by_name("reporting", {"report": "Alice", "manager": "Zed"}, utc("2025-01-15"))
    assert nobody.answer is Answer.NOT_YET_KNOWN and nobody.steps == ["no referent named 'Zed'"]
    memory.ingest(Batch(referents=(Referent("p:bob-2", "person", "Bob"),)))  # a second, unmerged "Bob"
    ambiguous = memory.query_by_name("reporting", {"report": "Alice", "manager": "Bob"}, utc("2025-01-15"))
    assert ambiguous.answer is Answer.UNKNOWN and ambiguous.ambiguous == ["Bob"]


def test_names_are_resolved_as_of_the_belief_time(memory, clock):
    """A referent first mentioned after the belief time must not leak into an as-of answer."""
    from gupi.extraction.pipeline import extract
    from gupi.extraction.rules import RuleExtractor
    from gupi.records import Context, Observation
    ctx = Context("conv:z", "conversation")
    early = Observation(HR.id, "z-1", "Ann Kay reports to Ben Ross.", utc("2025-01-10"), ctx.id)
    late = Observation(HR.id, "z-2", "Cleo Park reports to Ben Ross.", utc("2025-06-10"), ctx.id)
    for obs in (early, late):
        clock.set(obs.observed_at.isoformat()[:16])
        memory.ingest(Batch((HR,), (obs,), contexts=(ctx,)))
        extract(memory, RuleExtractor(), [obs])
    before = memory.query_by_name("reporting", {"report": "Cleo Park", "manager": "Ben Ross"}, utc("2025-01-15"),
                                  believed_at=utc("2025-03-01"))
    assert before.answer is Answer.NOT_YET_KNOWN and before.steps == ["no referent named 'Cleo Park'"]


def test_v1_excludes_an_explicit_negation_instead_of_reading_it_as_positive(memory, clock):
    neg = observe(HR, "hr-n", "Alice does not report to Bob.", "2025-04-01")
    c_neg = reports(neg, valid=ValidTime(to_earliest=utc("2025-04-01")), polarity="negative")
    clock.set("2025-04-02")
    record(memory, [neg], [c_neg])
    memory.review(c_neg.id, "accepted", "reviewer")
    r = memory.query(Question("reporting", {"report": "p:alice", "manager": "p:bob"}, utc("2025-03-15")))
    assert r.answer is Answer.UNKNOWN and r.citations == []
    assert (c_neg.id, "an explicit negation, which answer semantics v1 cannot express") in r.excluded
