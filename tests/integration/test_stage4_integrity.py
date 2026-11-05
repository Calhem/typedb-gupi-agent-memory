"""Phase 7B Stage 4 (R1–R3) through the durable candidate store on a live TypeDB: what is recorded, what waits
for review, and what becomes a claim. Synthetic, developer-authored fixtures."""

import sys
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
