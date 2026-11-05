"""Phase 7B Stage 4 (R1–R3) through the durable candidate store on a live TypeDB: what is recorded, what waits
for review, and what becomes a claim. Synthetic, developer-authored fixtures."""

import sys
from datetime import timedelta
from pathlib import Path

import pytest

from gupi.formation import store
from gupi.memory import Memory
from gupi.query import Question
from gupi.temporal import Answer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import utc  # noqa: E402
from test_model_candidate_store import assertion, response, submit  # noqa: E402

pytestmark = pytest.mark.integration
ORG = "organization"


def test_r1_unverified_statement_waits_for_review_and_forms_only_on_approval(memory, clock):
    text = "Brackwater Audit has opened an inquiry into Lena Ostrow."
    bad = response(assertion(text.rstrip("."), [("subject", "Brackwater Audit", ORG), ("object", "Lena Ostrow", "person")],
                             relation="statement", predicate="has opened", object_text="an inquiry"))
    (s,), _, _ = submit(memory, clock, text, bad, "r1-a")
    assert s.status == "review" and "statement structure not verified" in s.decisions[-1].reason
    assert s.claim_id is None and not memory.all_claims()
    assert s.candidate.id in {c.candidate.id for c in store.pending(memory)}

    good_text = "Halden Holdings has opened an inquiry into Pellwick."
    good = response(assertion(good_text.rstrip("."), [("subject", "Halden Holdings", ORG), ("object", "Pellwick", ORG)],
                              relation="statement", predicate="has opened an inquiry into"))
    (g,), _, _ = submit(memory, clock, good_text, good, "r1-b")
    assert g.status == "formed" and g.claim_id

    store.review(memory, s.candidate.id, "approve", "reviewer-a", "checked against the source")
    after = store.get(memory, s.candidate.id)
    assert [d.outcome for d in after.decisions] == ["review", "formed"] and after.claim_id
    assert len(memory.all_claims()) == 2


def test_r2_bare_retraction_is_stored_for_review_and_supersedes_nothing(memory, clock):
    earlier = "Tomas Reyl joined Halden in March 2025."
    (e,), _, _ = submit(memory, clock, earlier, response(assertion(
        earlier.rstrip("."), [("employee", "Tomas Reyl", "person"), ("employer", "Halden", ORG)],
        times=[("March 2025", "start")])), "r2-a")
    assert e.status == "formed"

    text = "Apologies, please disregard what I wrote this morning about Tomas, wrong person."
    (r,), report, _ = submit(memory, clock, text, response(outcome="no-relevant-assertion"), "r2-b")
    assert r.status == "review" and r.claim_id is None
    assert "target is not established" in r.decisions[-1].reason
    assert r.candidate.id in {c.candidate.id for c in store.pending(memory)}
    assert all(s.resolution in ("missing", "ambiguous") for s in store.suggestions(memory, r.candidate.id))

    # the retracted claim is untouched: still formed, still believed
    assert store.get(memory, e.candidate.id).status == "formed"
    assert e.claim_id in memory.believed_ids(clock.now)

    clock.now += timedelta(minutes=1)
    store.review(memory, r.candidate.id, "approve", "reviewer-a", "the author confirmed the retraction")
    assert store.get(memory, r.candidate.id).claim_id
    assert e.claim_id in memory.believed_ids(clock.now)  # approving the retraction supersedes nothing


def test_r3_fact_inside_an_allegation_is_never_formed_as_established(memory, clock):
    text = "The lawsuit alleges that Corvane Freight's finance director, Ilse Marrow, hid losses from auditors."
    lawsuit = {"mode": "reported", "claimant": "The lawsuit", "claimant_kind": "unknown", "via": []}
    resp = response(
        assertion(text.rstrip("."), [("subject", "Ilse Marrow", "person")], relation="statement", predicate="hid",
                  object_text="losses from auditors", attribution=lawsuit, allegation=True),
        assertion("Corvane Freight's finance director, Ilse Marrow",
                  [("employee", "Ilse Marrow", "person"), ("employer", "Corvane Freight", ORG)], title="finance director"))
    stored, _, _ = submit(memory, clock, text, resp, "r3-a")
    assert [s.status for s in stored] == ["review", "review"] and not memory.all_claims()

    emp = next(s for s in stored if s.candidate.claim_type == "employment")
    clock.now += timedelta(minutes=1)
    store.review(memory, emp.candidate.id, "approve", "reviewer-a", "the role is not disputed")
    (claim,) = memory.all_claims()
    # what memory holds is the lawsuit's report, uncommitted: never an unqualified fact of the author's
    assert (claim.commitment, claim.attribution_mode) == ("unknown", "reported")


# --- final review: persistence and retrieval --------------------------------------------------------------

def ask(memory, claim, at):
    return memory.query(Question(claim.type, {r: v[0] for r, v in claim.roles.items()}, utc(at), semantics="v2"))


def answer_of(memory, claim, at="2025-04-01"):
    r = ask(memory, claim, at)
    return r.answer, tuple(sorted(c.claim_id for c in r.citations))


@pytest.mark.parametrize("verdict", ["approve", "reject"])
def test_r2_review_item_survives_a_new_connection_and_changes_no_answer(memory, clock, driver, database, verdict):
    earlier = "Tomas Reyl worked at Halden from March 2025 to May 2025."
    (e,), _, _ = submit(memory, clock, earlier, response(assertion(
        earlier.rstrip("."), [("employee", "Tomas Reyl", "person"), ("employer", "Halden", ORG)],
        times=[("March 2025", "start"), ("May 2025", "end")])), "p-a")
    (claim,) = memory.all_claims()
    before, believed = answer_of(memory, claim), memory.believed_ids(clock.now)
    assert before[0] is Answer.TRUE and before[1] == (claim.id,)

    text = "Apologies, please disregard what I wrote this morning about Tomas, wrong person."
    (r,), _, _ = submit(memory, clock, text, response(outcome="no-relevant-assertion"), "p-b")

    reopened = Memory(driver, database, clock=clock, packs=("core", "people"))  # nothing held in this process
    kept = store.get(reopened, r.candidate.id)
    assert kept.status == "review" and kept.candidate == r.candidate
    assert kept.candidate.relations[0].target is None and kept.payload == r.payload
    assert r.candidate.id in {c.candidate.id for c in store.pending(reopened)}
    assert store.suggestions(reopened, r.candidate.id)
    assert answer_of(reopened, claim) == before and set(reopened.believed_ids(clock.now)) == set(believed)

    clock.now += timedelta(minutes=1)
    store.review(reopened, r.candidate.id, verdict, "reviewer-a", "checked with the author")
    assert answer_of(reopened, claim) == before                         # a decision on it changes no answer
    assert e.claim_id in reopened.believed_ids(clock.now)
    assert r.candidate.id not in {c.candidate.id for c in store.pending(reopened)}
    assert [d.outcome for d in store.get(reopened, r.candidate.id).decisions][0] == "review"  # history kept


def test_r3_attribution_and_uncertainty_survive_persistence_and_retrieval(memory, clock, driver, database):
    text = "The lawsuit alleges that Ilse Marrow worked at Corvane Freight from May 2024 to June 2025 and hid losses."
    lawsuit = {"mode": "reported", "claimant": "The lawsuit", "claimant_kind": "unknown", "via": []}
    resp = response(
        assertion(text.rstrip("."), [("subject", "Ilse Marrow", "person")], relation="statement", predicate="hid",
                  object_text="losses", attribution=lawsuit, allegation=True),
        assertion("Ilse Marrow worked at Corvane Freight from May 2024 to June 2025",
                  [("employee", "Ilse Marrow", "person"), ("employer", "Corvane Freight", ORG)],
                  times=[("May 2024", "start"), ("June 2025", "end")]))
    stored, _, _ = submit(memory, clock, text, resp, "p-c")
    emp = next(s for s in stored if s.candidate.claim_type == "employment")
    assert emp.status == "review" and not memory.all_claims()   # unanswered until reviewed
    clock.now += timedelta(minutes=1)
    store.review(memory, emp.candidate.id, "approve", "reviewer-a", "kept as the lawsuit's report")

    reopened = Memory(driver, database, clock=clock, packs=("core", "people"))
    (claim,) = reopened.all_claims()
    assert (claim.commitment, claim.attribution_mode) == ("unknown", "reported")
    r = ask(reopened, claim, "2024-12-01")
    assert r.answer is Answer.TRUE   # temporal status and evidential standing stay separate dimensions
    q = r.qualification
    assert q.standing == "qualified" and q.definitive is False       # never an unqualified fact
    assert {"hedged:unknown", "reported"} <= set(q.qualifiers)
    assert q.originators == ("The lawsuit",)
    assert q.accepted_by == ("reviewer-a",)
    (c,) = r.citations
    assert c.quote == "Ilse Marrow worked at Corvane Freight from May 2024 to June 2025"
