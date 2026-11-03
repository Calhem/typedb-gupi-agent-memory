"""Phase 6C end to end against the live server: observation → rules:v2 candidates → formation decisions →
accepted claims → answers, citations and history (docs/formation/formation.md)."""

import dataclasses

import pytest
from helpers import CHAT, HR, PEOPLE, record, utc
from typedb.driver import TransactionType

from gupi import retrieval, typeql
from gupi.formation.form import POLICY, form
from gupi.formation.rules_v2 import RulesV2
from gupi.query import Question
from gupi.records import Batch, Observation, Referent
from gupi.temporal import Answer, ValidTime
from gupi.typedb.connection import transaction

pytestmark = pytest.mark.integration


def observe(memory, clock, text, at="2025-08-20", key="k1", source=HR, author=None):
    obs = Observation(source.id, key, text, utc(at), author_id=author)
    clock.set(at)
    record(memory, [obs], [])
    return obs


def run(memory, clock, text, approvals=None, prior=(), **kw):
    obs = observe(memory, clock, text, **kw)
    cset, _ = RulesV2().extract(obs, prior=prior)
    return obs, cset, form(memory, obs, cset, approvals)


def view(memory, claim_id):
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        return retrieval.claim(tx, claim_id)


def ask(memory, c, at, believed_at=None, semantics="v2"):
    return memory.ask(c.type, dict(c.roles), utc(at), believed_at=utc(believed_at) if believed_at else None,
                      semantics=semantics)


# --- what is formed ------------------------------------------------------------------------------------

def test_an_ordinary_assertion_is_formed_and_accepted_with_its_provenance(memory, clock):
    obs, cset, r = run(memory, clock, "Alice Grey works at Acme Labs as Head of Data.")
    assert r.counts() == {"formed": 1, "withheld": 0, "review": 0, "rejected": 0}
    (d,) = r.decisions
    c = view(memory, d.claim_id)
    assert (c.method, c.candidate_id, c.commitment, c.attribution_mode, c.values) == \
        ("rules:v2", cset.candidates[0].id, "certain", "direct", {"job-title": "Head of Data"})
    (review,) = c.reviews
    assert (review.verdict, review.decided_by) == ("accepted", POLICY) and cset.candidates[0].id in review.reason
    assert ask(memory, c, "2025-08-20").answer is Answer.TRUE


def test_lower_bound_continuity_never_becomes_an_exact_start(memory, clock):
    _, _, r = run(memory, clock, "Alice Grey has worked at Acme Labs since March 2025.")
    c = view(memory, r.decisions[0].claim_id)
    assert c.valid == ValidTime(None, utc("2025-04-01"), utc("2025-08-20")) and c.valid_from_basis == "lower-bound"
    assert ask(memory, c, "2025-03-15").answer is Answer.UNKNOWN   # maybe before, maybe after it began
    assert ask(memory, c, "2025-06-01").answer is Answer.TRUE      # certainly held from 1 April
    assert ask(memory, c, "2024-12-01").answer is Answer.UNKNOWN   # never FALSE: the start is not stated


def test_an_explicit_negation_is_formed_as_a_negation(memory, clock):
    _, _, r = run(memory, clock, "Alice Grey no longer works at Acme Labs.")
    c = view(memory, r.decisions[0].claim_id)
    assert c.polarity == "negative" and c.valid.to_latest is None    # no invented end date
    assert ask(memory, c, "2025-08-20").answer is Answer.FALSE
    assert ask(memory, c, "2025-08-20", semantics="v1").answer is Answer.UNKNOWN  # v1 cannot express it


# --- what waits for review, or is withheld -------------------------------------------------------------

def test_a_hedged_assertion_waits_for_review_then_keeps_its_uncertainty(memory, clock):
    obs, cset, r = run(memory, clock, "I think Alice Grey reports to Bo Kim.")
    assert r.counts()["review"] == 1 and memory.all_claims() == []
    (cand,) = cset.candidates
    approved = form(memory, obs, cset, approvals={cand.id: "reviewer-a"})
    (d,) = approved.decisions
    c = view(memory, d.claim_id)
    assert (d.outcome, d.decided_by, c.commitment) == ("formed", "reviewer-a", "probable")
    assert (c.reviews[0].verdict, c.reviews[0].decided_by) == ("accepted", "reviewer-a")


def test_plans_and_hypotheticals_are_withheld(memory, clock):
    obs, cset, r = run(memory, clock, "Alice Grey will join Acme Labs in October 2025.")
    assert [(d.outcome, "planned" in d.reason) for d in r.decisions] == [("withheld", True)]
    hypothetical = dataclasses.replace(cset, candidates=(dataclasses.replace(cset.candidates[0], modality="hypothetical"),))
    assert form(memory, obs, hypothetical).counts()["withheld"] == 1
    assert memory.all_claims() == []


def test_a_correction_is_routed_to_review_and_never_supersedes(memory, clock):
    _, first_set, first = run(memory, clock, "Alice Grey joined Acme Labs in March 2025.", key="k1", at="2025-04-02")
    obs, cset, r = run(memory, clock, "Correction: Alice Grey joined Acme Labs in April 2025, not March.",
                       key="k2", at="2025-05-02", prior=(first_set,))
    assert [d.outcome for d in r.decisions] == ["review"] and len(memory.all_claims()) == 1
    approved = form(memory, obs, cset, approvals={cset.candidates[0].id: "reviewer-a"})
    (d,) = approved.decisions
    assert d.suggestion["old"] == first.decisions[0].claim_id and d.suggestion["new"] == d.claim_id
    old = view(memory, first.decisions[0].claim_id)
    assert old.supersessions == () and old.superseded_by == ()          # nothing was overwritten
    assert {c.id for c in memory.all_claims()} == {old.id, d.claim_id}


def test_a_forwarded_copy_is_not_a_second_attestation(memory, clock):
    text = ("Alice Grey has reported to Bo Kim since April 2025.\n---- Forwarded message ----\n"
            "Alice Grey has reported to Bo Kim since April 2025.")
    _, _, r = run(memory, clock, text)
    assert [d.outcome for d in r.decisions] == ["formed", "withheld"] and "not an independent" in r.decisions[1].reason
    assert len(memory.all_claims()) == 1


def test_malformed_or_unsupported_candidates_are_rejected_and_form_nothing(memory, clock):
    obs, cset, _ = run(memory, clock, "Corbel is hiring.")
    assert cset.candidates == ()
    obs, cset, _ = run(memory, clock, "Alice Grey joined Acme Labs in March 2025.", key="k2")
    claims_before = {c.id for c in memory.all_claims()}
    c = cset.candidates[0]
    broken = dataclasses.replace(cset, candidates=(dataclasses.replace(c, passage=dataclasses.replace(c.passage, text="x")),))
    r = form(memory, obs, broken)
    assert r.counts()["rejected"] == 1 and "malformed" in r.decisions[0].reason
    assert form(memory, obs, dataclasses.replace(cset, content_hash="nope")).counts()["rejected"] == 1
    assert {c.id for c in memory.all_claims()} == claims_before


# --- identity, idempotency, history, provenance ---------------------------------------------------------

def test_repeated_formation_writes_nothing_new(memory, clock):
    obs, cset, first = run(memory, clock, "Alice Grey works at Acme Labs.")
    clock.set("2025-08-21")
    again = form(memory, obs, cset)
    assert again.already_formed and [d.claim_id for d in again.decisions] == [d.claim_id for d in first.decisions]
    (c,) = memory.all_claims()
    assert len(c.reviews) == 1
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        runs = typeql.concept_rows(tx, "match $r isa extraction-run, has method == $m;", {"m": POLICY})
    assert len(runs) == 1


def test_no_silent_entity_merging_across_observations(memory, clock):
    _, _, a = run(memory, clock, "Alice Grey works at Acme Labs.", key="k1")
    _, _, b = run(memory, clock, "Alice Grey works at Acme Labs.", key="k2", source=CHAT)
    ca, cb = view(memory, a.decisions[0].claim_id), view(memory, b.decisions[0].claim_id)
    assert ca.roles["employee"] != cb.roles["employee"]   # same name, different sources: not merged here
    assert memory.identity_claims() == []                  # merging stays an explicit identity decision


def test_belief_time_history_is_reproducible(memory, clock):
    _, _, r = run(memory, clock, "Alice Grey works at Acme Labs.", at="2025-08-20")
    c = view(memory, r.decisions[0].claim_id)
    assert ask(memory, c, "2025-08-20", believed_at="2025-08-19").answer is Answer.NOT_YET_KNOWN
    assert ask(memory, c, "2025-08-20", believed_at="2025-08-21").answer is Answer.TRUE


def test_citations_point_to_the_exact_passage_and_the_asserter(memory, clock):
    memory.ingest(Batch(referents=(Referent("p:wen", "person", "Wen"),)))
    text = "Hello all. Ravi told me that Alice Grey left Acme Labs in May 2025."
    obs, cset, r = run(memory, clock, text, source=CHAT, author="p:wen")
    c = view(memory, r.decisions[0].claim_id)
    passage = "Ravi told me that Alice Grey left Acme Labs in May 2025."
    assert (c.evidence[0].quote, c.evidence[0].span_start) == (passage, text.index(passage))
    assert c.attribution_mode == "reported"
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        asserter = retrieval.asserters(tx, [c.id])[c.id]
        labels = {d["l"] for d in typeql.documents(tx, 'match $x isa referent, has gupi-id == $id; fetch { "l": $x.label };', {"id": asserter})}
    assert labels == {"Ravi"}
    res = memory.query(Question(c.type, {r: v[0] for r, v in c.roles.items()}, utc("2025-07-01"), semantics="v2"))
    assert res.answer is Answer.FALSE
    (cite,) = res.citations
    assert (cite.quote, cite.observation_id, cite.said_at, cite.verdict) == (passage, obs.id, utc("2025-08-20"), "ended")
