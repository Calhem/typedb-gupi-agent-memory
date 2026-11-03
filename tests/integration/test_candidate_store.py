"""The candidate store (core/0012; gupi.formation.store) against the live server: durable candidates,
append-only decisions, atomic formation, correction suggestions, restarts and history."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from helpers import CHAT, HR, observe as legacy_observe, record, reports, utc
from typedb.driver import TransactionType

from gupi import retrieval, typeql
from gupi.formation import store
from gupi.formation.candidate import from_dict
from gupi.formation.rules_v2 import RulesV2
from gupi.records import Batch, Context, Observation
from gupi.temporal import Answer, ValidTime
from gupi.typedb.connection import transaction

pytestmark = pytest.mark.integration
THREAD = Context("ctx:thread", "conversation")
HERE = Path(__file__).resolve().parent


def say(memory, clock, key, text, at, source=HR, author=None):
    obs = Observation(source.id, key, text, utc(at), THREAD.id, author)
    clock.set(at)
    memory.ingest(Batch(sources=(source,), observations=(obs,), contexts=(THREAD,)))
    cset, _ = RulesV2().extract(obs)
    return obs, cset, store.submit(memory, obs, cset)


def claims(memory):
    return memory.all_claims()


# --- persistence and retrieval -------------------------------------------------------------------------

def test_a_candidate_is_stored_exactly_and_retrieved_by_id_without_forming_a_claim(memory, clock):
    obs, cset, r = say(memory, clock, "m1", "I think Alice Grey works at Acme Labs.", "2025-06-01T09:00")
    (c,) = cset.candidates
    assert r.stored == [c.id] and [d.outcome for d in r.decisions] == ["review"] and claims(memory) == []
    s = store.get(memory, c.id)
    assert s.candidate == c and s.payload == store.payload(cset, c)                 # exact round trip
    assert from_dict(json.loads(s.payload)).candidates[0].id == c.id
    assert (s.observation_id, s.extractor, s.ir_version, s.status) == (obs.id, "rules:v2", "gupi.candidate/1", "review")
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        (span,) = typeql.documents(tx, "match $c isa memory-candidate, has gupi-id == $id; "
                                       "$l isa candidate-of (candidate: $c); fetch { $l.* };", {"id": c.id})
    assert (span["span-start"], span["span-end"]) == (c.passage.start, c.passage.end)
    assert [p.candidate.id for p in store.pending(memory)] == [c.id]


def test_withheld_and_formed_candidates_are_kept_with_their_decisions(memory, clock):
    _, plan, _ = say(memory, clock, "m1", "Alice Grey will join Acme Labs in October 2025.", "2025-06-01T09:00")
    _, fact, _ = say(memory, clock, "m2", "Alice Grey works at Acme Labs.", "2025-06-01T09:00")
    p, f = store.get(memory, plan.candidates[0].id), store.get(memory, fact.candidates[0].id)
    assert (p.status, p.claim_id) == ("withheld", None)
    assert f.status == "formed" and f.claim_id == claims(memory)[0].id and claims(memory)[0].candidate_id == f.candidate.id


# --- review --------------------------------------------------------------------------------------------

def test_approval_forms_the_claim_and_keeps_the_uncertainty(memory, clock):
    _, cset, _ = say(memory, clock, "m1", "I think Alice Grey works at Acme Labs.", "2025-06-01T09:00")
    cid = cset.candidates[0].id
    clock.set("2025-06-02")
    d = store.review(memory, cid, "approve", "reviewer-a", "confirmed by phone")
    s = store.get(memory, cid)
    (claim,) = claims(memory)
    assert (d.outcome, d.decided_by, s.status, s.claim_id) == ("formed", "reviewer-a", "formed", claim.id)
    assert "confirmed by phone" in d.reason and d.at == utc("2025-06-02")
    assert claim.commitment == "probable" and claim.reviews[-1].decided_by == "reviewer-a"
    q = memory.ask(claim.type, dict(claim.roles), utc("2025-06-01T09:00"), semantics="v2").qualification
    assert (q.standing, q.definitive) == ("qualified", False)          # approval did not make it certain


def test_rejection_keeps_the_candidate_and_forms_nothing(memory, clock):
    _, cset, _ = say(memory, clock, "m1", "I think Alice Grey works at Acme Labs.", "2025-06-01T09:00")
    cid = cset.candidates[0].id
    clock.set("2025-06-02")
    d = store.review(memory, cid, "reject", "reviewer-b", "no second source")
    s = store.get(memory, cid)
    assert (d.outcome, s.status, s.claim_id, claims(memory)) == ("rejected", "rejected", None, [])
    assert store.pending(memory) == [] and s.candidate == cset.candidates[0]


def test_decisions_are_append_only_with_history_preserved(memory, clock):
    _, cset, _ = say(memory, clock, "m1", "I think Alice Grey works at Acme Labs.", "2025-06-01T09:00")
    cid = cset.candidates[0].id
    clock.set("2025-06-02")
    store.review(memory, cid, "reject", "reviewer-a", "unsure")
    clock.set("2025-06-03")
    store.review(memory, cid, "approve", "reviewer-b", "now confirmed")
    s = store.get(memory, cid)
    assert [(d.outcome, d.decided_by) for d in s.decisions] == \
        [("review", "formation:v1"), ("rejected", "reviewer-a"), ("formed", "reviewer-b")]
    assert s.status_at(utc("2025-06-02T12:00")) == "rejected" and s.status_at(utc("2025-06-01T12:00")) == "review"
    with pytest.raises(ValueError, match="already formed"):
        store.review(memory, cid, "reject", "reviewer-c")
    clock.set("2025-06-03")  # a stalled clock is refused rather than allowed to blur the order
    _, other, _ = say(memory, clock, "m2", "I think Alice Grey reports to Bo Kim.", "2025-06-03")
    with pytest.raises(ValueError, match="clock has not advanced"):
        store.review(memory, other.candidates[0].id, "reject", "reviewer-a")


def test_approving_a_plan_never_makes_it_a_fact(memory, clock):
    _, cset, _ = say(memory, clock, "m1", "Alice Grey will join Acme Labs in October 2025.", "2025-06-01T09:00")
    clock.set("2025-06-02")
    d = store.review(memory, cset.candidates[0].id, "approve", "reviewer-a")
    assert d.outcome == "withheld" and "approval cannot form it" in d.reason and claims(memory) == []


# --- idempotency and atomicity -------------------------------------------------------------------------

def test_repeated_submission_and_review_record_nothing_new(memory, clock):
    obs, cset, _ = say(memory, clock, "m1", "I think Alice Grey works at Acme Labs.", "2025-06-01T09:00")
    cid = cset.candidates[0].id
    again = store.submit(memory, obs, cset)
    assert again.stored == [cid] and again.decisions == []
    clock.set("2025-06-02")
    store.review(memory, cid, "reject", "reviewer-a", "unsure")
    assert store.review(memory, cid, "reject", "reviewer-a", "unsure") is None
    assert store.submit(memory, obs, cset).decisions == []            # a re-run never overrides a reviewer
    assert [d.outcome for d in store.get(memory, cid).decisions] == ["review", "rejected"]
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        assert len(typeql.concept_rows(tx, "match $c isa memory-candidate;")) == 1


def test_formation_and_its_decision_commit_together_or_not_at_all(memory, clock, monkeypatch):
    _, cset, _ = say(memory, clock, "m1", "I think Alice Grey works at Acme Labs.", "2025-06-01T09:00")
    cid = cset.candidates[0].id

    clock.set("2025-06-02")

    def fail(*a, **k):
        raise RuntimeError("simulated failure after the claim was written")
    monkeypatch.setattr(store, "_insert_decision", fail)
    with pytest.raises(RuntimeError):
        store.review(memory, cid, "approve", "reviewer-a")
    assert claims(memory) == [] and store.get(memory, cid).status == "review"   # rolled back entirely
    monkeypatch.undo()
    assert store.review(memory, cid, "approve", "reviewer-a").outcome == "formed" and len(claims(memory)) == 1


# --- corrections ---------------------------------------------------------------------------------------

def test_correction_suggestions_with_known_missing_and_ambiguous_targets(memory, clock):
    _, _, missing = say(memory, clock, "m0", "Correction: Alice Grey joined Acme Labs in April 2025, not March.",
                        "2025-04-01T09:00")
    (s0,) = store.suggestions(memory, missing.stored[0])
    assert (s0.resolution, s0.targets) == ("missing", ())
    _, first, _ = say(memory, clock, "m1", "Alice Grey joined Acme Labs in March 2025.", "2025-04-02T09:00")
    _, fix, _ = say(memory, clock, "m2", "Correction: Alice Grey joined Acme Labs in May 2025, not March.",
                    "2025-05-02T09:00")
    (s1,) = store.suggestions(memory, fix.candidates[0].id)
    first_claim = store.get(memory, first.candidates[0].id).claim_id
    assert (s1.resolution, s1.targets) == ("resolved", (first_claim,))
    say(memory, clock, "m3", "Alice Grey works at Acme Labs.", "2025-05-03T09:00")
    _, amb, _ = say(memory, clock, "m4", "Correction: Alice Grey joined Acme Labs in June 2025.", "2025-06-02T09:00")
    (s2,) = store.suggestions(memory, amb.candidates[0].id)
    assert s2.resolution == "ambiguous" and len(s2.targets) == 2
    assert all(c.superseded_by == () for c in claims(memory))           # nothing was applied


# --- provenance, meaning, history, compatibility ------------------------------------------------------

def test_provenance_and_temporal_meaning_survive_storage_and_formation(memory, clock):
    from gupi.records import Referent
    memory.ingest(Batch(referents=(Referent("p:wen", "person", "Wen Abara"),)))
    _, cset, _ = say(memory, clock, "m1", "According to Bo Kim, Alice Grey has worked at Acme Labs since March 2025.",
                     "2025-08-01T09:00", author="p:wen")
    s = store.get(memory, cset.candidates[0].id)
    assert s.status == "formed" and s.candidate.attribution.asserted_by == "Bo Kim"
    c = next(x for x in claims(memory) if x.id == s.claim_id)
    assert c.valid == ValidTime(None, utc("2025-04-01"), utc("2025-08-01T09:00")) and c.valid_from_basis == "lower-bound"
    assert c.attribution_mode == "reported"
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        assert retrieval.asserters(tx, [c.id])[c.id] != "p:wen"           # the speaker, not the author


def test_a_forwarded_copy_is_stored_but_withheld(memory, clock):
    say(memory, clock, "m1", "Alice Grey works at Acme Labs.", "2025-06-01T09:00")
    _, cset, _ = say(memory, clock, "m2", "FYI\n---- Forwarded message ----\nAlice Grey works at Acme Labs.",
                     "2025-06-02T09:00")
    s = store.get(memory, cset.candidates[0].id)
    assert s.status == "withheld" and "not an independent attestation" in s.decisions[-1].reason
    assert len(claims(memory)) == 1


def test_pending_and_status_follow_belief_time(memory, clock):
    _, cset, _ = say(memory, clock, "m1", "I think Alice Grey works at Acme Labs.", "2025-06-01T09:00")
    cid = cset.candidates[0].id
    clock.set("2025-06-05")
    store.review(memory, cid, "approve", "reviewer-a")
    assert [s.candidate.id for s in store.pending(memory, at=utc("2025-06-02"))] == [cid]
    assert store.pending(memory, at=utc("2025-05-31")) == [] and store.pending(memory) == []
    c = claims(memory)[0]
    assert memory.ask(c.type, dict(c.roles), utc("2025-06-01T09:00"), believed_at=utc("2025-06-02"),
                      semantics="v2").answer is Answer.NOT_YET_KNOWN     # not in memory before it was formed


def test_existing_queries_are_unchanged_by_stored_candidates(memory, clock):
    o = legacy_observe(HR, "hr-1", "Alice reports to Bob.", "2025-03-01")
    c = reports(o, valid=ValidTime(to_earliest=utc("2025-03-01")))
    clock.set("2025-03-02")
    record(memory, [o], [c])
    memory.review(c.id, "accepted", "reviewer")
    roles = {"report": "p:alice", "manager": "p:bob"}
    before = (memory.ask("reporting", roles, utc("2025-02-15")).answer,
              memory.ask("reporting", roles, utc("2025-03-01"), semantics="v2").answer)
    obs = Observation(CHAT.id, "c1", "I think Alice Grey reports to Bo Kim.", utc("2025-03-03"), THREAD.id)
    clock.set("2025-03-03")
    memory.ingest(Batch(sources=(CHAT,), observations=(obs,), contexts=(THREAD,)))
    store.submit(memory, obs, RulesV2().extract(obs)[0])
    after = (memory.ask("reporting", roles, utc("2025-02-15")).answer,
             memory.ask("reporting", roles, utc("2025-03-01"), semantics="v2").answer)
    assert before == after == (Answer.UNKNOWN, Answer.TRUE)


# --- restart: separate processes, separate connections -------------------------------------------------

def process(database, *args):
    out = subprocess.run([sys.executable, "-I", str(HERE / "store_process.py"), database, *args],
                         capture_output=True, text=True, timeout=120, check=True)
    return json.loads(out.stdout.strip().splitlines()[-1])


def test_pending_review_survives_process_restarts(memory, database):
    submitted = process(database, "submit")                    # process 1: extract and store, then exit
    (cid,) = submitted["stored"]
    assert submitted["outcomes"] == ["review"]
    assert process(database, "pending") == {"pending": [cid]}  # process 2: a fresh connection still sees it
    assert process(database, "approve", cid) == {"outcome": "formed", "decided_by": "reviewer-a"}  # process 3
    shown = process(database, "show", cid)                     # process 4: the full history is durable
    assert shown["status"] == "formed" and shown["decisions"] == [["review", "formation:v1"], ["formed", "reviewer-a"]]
    assert store.get(memory, cid).payload == shown["payload"] and len(memory.all_claims()) == 1


def test_an_altered_payload_is_detected_on_reading(memory, clock):
    _, cset, _ = say(memory, clock, "m1", "I think Alice Grey works at Acme Labs.", "2025-06-01T09:00")
    cid = cset.candidates[0].id
    tampered = store.get(memory, cid).payload.replace("probable", "certain")
    with transaction(memory.driver, memory.database, TransactionType.WRITE) as tx:
        typeql.run(tx, "match $c isa memory-candidate, has gupi-id == $id; update $c has candidate-payload == $p;",
                   {"id": cid, "p": tampered})
    with pytest.raises(ValueError, match="does not match its payload"):
        store.get(memory, cid)
