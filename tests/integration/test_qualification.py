"""Evidential standing of v2 answers: kept separate from the temporal status and from acceptance
(gupi.qualification; docs/formation/6c-hardening.md)."""

import pytest
from helpers import CHAT, HR, observe as legacy_observe, record, reports, utc

from gupi.extraction.contract import referent_id
from gupi.formation.form import POLICY, form
from gupi.formation.rules_v2 import RulesV2
from gupi.query import Question
from gupi.records import Batch, Context, Observation, Referent
from gupi.temporal import Answer, ValidTime

pytestmark = pytest.mark.integration
CTX = Context("ctx:q", "conversation")
ROLES = {"employee": referent_id(CTX.id, "person", "Alice Grey"), "employer": referent_id(CTX.id, "organization", "Acme Labs")}


def say(memory, clock, key, text, at, author=None, source=HR, approve=None, recorded=None):
    obs = Observation(source.id, key, text, utc(at), CTX.id, author)
    clock.set(recorded or at)
    memory.ingest(Batch(sources=(source,), observations=(obs,), contexts=(CTX,)))
    cset, _ = RulesV2().extract(obs)
    approvals = {c.id: approve for c in cset.candidates} if approve else {}
    return form(memory, obs, cset, approvals)


def ask(memory, at, believed_at=None, semantics="v2"):
    return memory.ask("employment", ROLES, utc(at), believed_at=utc(believed_at) if believed_at else None,
                      semantics=semantics)


@pytest.fixture
def people(memory):
    memory.ingest(Batch(referents=(Referent("p:wen", "person", "Wen Abara"), Referent("p:bo", "person", "Bo Kim"))))


def test_direct_evidence_gives_a_definitive_answer(memory, clock, people):
    say(memory, clock, "m1", "Alice Grey works at Acme Labs.", "2025-06-01T09:00", author="p:wen")
    r = ask(memory, "2025-06-01T09:00")
    q = r.qualification
    assert r.answer is Answer.TRUE and (q.standing, q.definitive, q.qualifiers) == ("direct", True, ())
    assert (q.originators, q.independent, q.accepted_by) == (("Wen Abara",), 1, (POLICY,))
    assert "admission is not verification" in q.explanation


def test_hedged_evidence_approved_by_review_stays_qualified(memory, clock):
    say(memory, clock, "m1", "I think Alice Grey works at Acme Labs.", "2025-06-01T09:00", approve="reviewer-a")
    r = ask(memory, "2025-06-01T09:00")
    q = r.qualification
    assert r.answer is Answer.TRUE                                       # the temporal status is unchanged
    assert (q.standing, q.definitive, q.qualifiers, q.accepted_by) == ("qualified", False, ("hedged:probable",), ("reviewer-a",))
    assert "not definitive" in q.explanation


def test_reported_evidence_keeps_its_speaker(memory, clock, people):
    say(memory, clock, "m1", "Ravi told me that Alice Grey left Acme Labs in May 2025.", "2025-06-01T09:00", author="p:wen")
    q = ask(memory, "2025-07-01").qualification
    assert (q.standing, q.definitive, q.qualifiers, q.originators) == ("qualified", False, ("reported",), ("Ravi",))


def test_independence_counts_originators_not_documents(memory, clock, people):
    say(memory, clock, "m1", "Alice Grey works at Acme Labs.", "2025-06-01T09:00", author="p:wen")
    say(memory, clock, "m2", "Alice Grey works at Acme Labs.", "2025-06-01T09:00", author="p:wen", source=CHAT)
    assert ask(memory, "2025-06-01T09:00").qualification.independent == 1        # one speaker, twice
    say(memory, clock, "m3", "Alice Grey works at Acme Labs.", "2025-06-01T09:00", author="p:bo", source=CHAT)
    assert ask(memory, "2025-06-01T09:00").qualification.independent == 2


def test_contested_answers_are_never_definitive(memory, clock, people):
    say(memory, clock, "m1", "Alice Grey works at Acme Labs.", "2025-06-01T09:00", author="p:wen")
    say(memory, clock, "m2", "Ravi told me that Alice Grey no longer works at Acme Labs.", "2025-06-01T09:00",
        author="p:bo", source=CHAT)
    r = ask(memory, "2025-06-01T09:00")
    assert r.answer is Answer.CONTESTED and not r.qualification.definitive
    assert r.qualification.originators == ("Ravi", "Wen Abara") and "reported" in r.qualification.qualifiers


def test_history_excludes_later_evidence(memory, clock):
    say(memory, clock, "m1", "I think Alice Grey works at Acme Labs.", "2025-06-01T09:00", approve="reviewer-a")
    say(memory, clock, "m2", "Alice Grey works at Acme Labs.", "2025-06-01T09:00", source=CHAT, recorded="2025-06-05")
    clock.set("2025-06-10")
    before = ask(memory, "2025-06-01T09:00", believed_at="2025-06-02").qualification
    assert (before.standing, before.definitive) == ("qualified", False)
    after = ask(memory, "2025-06-01T09:00").qualification
    assert (after.standing, after.definitive, after.qualifiers) == ("direct", True, ("hedged:probable",))


def test_query_results_carry_the_qualification_beside_the_answer(memory, clock):
    say(memory, clock, "m1", "I think Alice Grey works at Acme Labs.", "2025-06-01T09:00", approve="reviewer-a")
    res = memory.query(Question("employment", ROLES, utc("2025-06-01T09:00"), semantics="v2"))
    assert res.answer is Answer.TRUE and res.qualification.standing == "qualified"
    assert res.bindings[0].qualification.qualifiers == ("hedged:probable",)
    assert memory.query(Question("employment", ROLES, utc("2025-06-01T09:00"))).qualification is None   # v1: none


def test_claims_without_formation_provenance_stay_backward_compatible(memory, clock):
    o = legacy_observe(HR, "hr-1", "Alice reports to Bob.", "2025-03-01")
    c = reports(o, valid=ValidTime(to_earliest=utc("2025-03-01")))
    clock.set("2025-03-02")
    record(memory, [o], [c])
    memory.review(c.id, "accepted", "reviewer")
    roles = {"report": "p:alice", "manager": "p:bob"}
    v1 = memory.ask("reporting", roles, utc("2025-02-15"))
    v2 = memory.ask("reporting", roles, utc("2025-03-01"), semantics="v2")
    assert v1.answer is Answer.UNKNOWN and v1.qualification is None
    q = v2.qualification
    assert v2.answer is Answer.TRUE and (q.standing, q.definitive, q.qualifiers) == ("unrecorded", True, ("provenance-not-recorded",))
