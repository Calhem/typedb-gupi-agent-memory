"""R2 (Phase 7B Stage 4): a retraction that does not restate what it retracts becomes a reviewable candidate with
an unestablished target. It is never dropped and never applied. Synthetic, developer-authored fixtures."""

from gupi.formation.form import decide

from test_model_candidate import assertion, kinds, response, run

EARLIER = "Tomas Reyl joined Halden in March 2025."
TOMAS = [("employee", "Tomas Reyl", "person"), ("employer", "Halden", "organization")]
RETRACTION = "Apologies, please disregard what I wrote this morning about Tomas, wrong person."
NOTHING = response(outcome="no-relevant-assertion")
REPORTED = response(problems=[{"kind": "insufficient-evidence", "evidence": RETRACTION,
                               "detail": "no assertion to carry a correction field"}])


def flags(report, kind):
    return [f["detail"] for f in report.flags if f["kind"] == kind]


def earlier_set():
    cset, _ = run(EARLIER, response(assertion(EARLIER.rstrip("."), TOMAS, times=[("March 2025", "start")])))
    return cset


def test_a_bare_retraction_becomes_a_reviewable_candidate():
    for resp in (NOTHING, REPORTED):  # whatever the model said, the message is read by code
        cset, report = run(RETRACTION, resp, prior=[earlier_set()])
        (c,) = cset.candidates
        assert c.claim_type == "statement" and c.passage.text == RETRACTION.rstrip(".")
        assert [(p.role, p.surface) for p in c.participants] == [("subject", "I")]
        assert dict(c.values) == {"predicate-text": "please disregard what I wrote", "object-text": "this morning about Tomas"}
        (r,) = c.relations
        assert (r.kind, r.target, r.marked) == ("retracts", None, "stated")
        d = decide(c, [], {})
        assert d.outcome == "review" and "target is not established" in d.reason
        assert flags(report, "retraction-possible-targets") == [earlier_set().candidates[0].id]


def test_possible_targets_are_listed_never_chosen():
    cset, report = run(RETRACTION, NOTHING)
    (c,) = cset.candidates
    assert c.relations[0].target is None and flags(report, "retraction-possible-targets") == ["none found in the thread"]


def test_two_cues_in_one_sentence_make_one_candidate():
    cset, _ = run("Sorry, ignore what I said about Tomas, I mixed him up with someone else.", NOTHING)
    assert len(cset.candidates) == 1


def test_a_reminder_is_not_a_retraction():
    for text in ("Don't forget what I said about the deadline.", "Tomas Reyl leads the audit team at Halden."):
        cset, report = run(text, NOTHING)
        assert cset.candidates == () and not flags(report, "bare-retraction")


def test_no_author_is_reported_not_silently_dropped():
    cset, report = run(RETRACTION, NOTHING, author=None)
    assert cset.candidates == () and kinds(report) == ["no-relevant-assertion", "bare-retraction-unrecorded"]


def test_a_retraction_the_model_already_carries_is_not_duplicated():
    text = "Correction: I take that back, Tomas Reyl did not join Halden."
    a = assertion("Tomas Reyl did not join Halden", TOMAS, polarity="negative",
                  correction={"kind": "retracts", "cue": "I take that back"})
    cset, _ = run(text, response(a), prior=[earlier_set()])
    assert [c.claim_type for c in cset.candidates] == ["employment"]


def test_approval_forms_the_retraction_but_never_its_target():
    cset, _ = run(RETRACTION, NOTHING, prior=[earlier_set()])
    (c,) = cset.candidates
    d = decide(c, [], {c.id: "reviewer-a"})
    assert d.outcome == "formed" and d.suggestion is None  # suggestions are made by form(), never applied
