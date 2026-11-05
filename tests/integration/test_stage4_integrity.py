"""Phase 7B Stage 4 (R1–R3) through the durable candidate store on a live TypeDB: what is recorded, what waits
for review, and what becomes a claim. Synthetic, developer-authored fixtures."""

import sys
from datetime import timedelta
from pathlib import Path

import pytest

from gupi.formation import store

sys.path.insert(0, str(Path(__file__).resolve().parent))
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
