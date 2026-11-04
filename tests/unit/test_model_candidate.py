"""model:candidate-v1, offline: recorded model-shaped responses -> candidates. The responses here are
developer-authored test inputs, not model output and not evaluation evidence."""

import copy
import json
from datetime import datetime, timezone

import pytest

from gupi.formation.model_candidate import METHOD, RESPONSE_FORMAT, ModelCandidateV1
from gupi.records import Observation

SAID = datetime(2025, 8, 20, 9, tzinfo=timezone.utc)


def obs(text, author="p:ivo-marsh", key="m1"):
    return Observation("src:t", key, text, SAID, "ctx:t", author)


def assertion(evidence, participants, relation="employment", times=(), **kw):
    a = {"evidence": evidence, "relation": relation,
         "participants": [{"role": r, "text": t, "kind": k, "is_pronoun_or_vague": False} for r, t, k in participants],
         "times": [{"text": t, "kind": k} for t, k in times], "polarity": "positive", "modality": "actual",
         "commitment": "certain", "attribution": {"mode": "direct", "claimant": None, "claimant_kind": None, "via": []},
         "basis": "explicit"}
    a.update(kw)
    return a


def response(*assertions, problems=(), outcome="assertions"):
    return {"format": RESPONSE_FORMAT, "outcome": outcome, "assertions": list(assertions), "problems": list(problems)}


NORA = [("employee", "Nora Vance", "person"), ("employer", "Halden", "organization")]


def run(text, resp, author="p:ivo-marsh", prior=()):
    return ModelCandidateV1().extract(obs(text, author), prior=prior, response=resp)


def kinds(report):
    return [o["kind"] for o in report.outcomes]


def test_a_grounded_assertion_becomes_a_candidate_with_computed_offsets():
    text = "Great news: Nora Vance joined Halden in March 2025."
    cset, report = run(text, response(assertion("Nora Vance joined Halden in March 2025", NORA, times=[("March 2025", "start")])))
    (c,) = cset.candidates
    assert cset.extractor.startswith(METHOD) and report.outcomes == []
    assert (c.passage.start, c.passage.end) == (12, 50) and text[c.passage.start:c.passage.end] == c.passage.text
    assert [(p.surface, text[p.start:p.end]) for p in c.participants] == [("Nora Vance", "Nora Vance"), ("Halden", "Halden")]
    (t,) = c.times
    assert (t.earliest.date().isoformat(), t.latest.date().isoformat(), t.precision) == ("2025-03-01", "2025-04-01", "month")


@pytest.mark.parametrize("resp, why", [
    ("{not json", "not JSON"),
    ({"format": "something-else/1", "outcome": "assertions", "assertions": [], "problems": []}, "format"),
    (response(dict(assertion("Nora Vance joined Halden", NORA), start=0)), "unexpected fields"),          # an offset
    (response({k: v for k, v in assertion("Nora Vance joined Halden", NORA).items() if k != "commitment"}), "missing"),
    (response(dict(assertion("Nora Vance joined Halden", NORA), commitment="definitely")), "commitment"),
    (response(assertion("Nora Vance joined Halden", NORA, times=[("March 2025", "start")])
              | {"times": [{"text": "March 2025", "kind": "start", "date": "2025-03-01"}]}), "unexpected fields"),  # a date
    (None, "no recorded response"),
])
def test_malformed_responses_produce_no_candidates(resp, why):
    cset, report = run("Nora Vance joined Halden in March 2025.", resp)
    assert cset.candidates == () and kinds(report) == ["invalid-model-output"] and why in report.outcomes[0]["detail"]


def test_quoted_text_must_occur_exactly():
    cset, report = run("Nora Vance joined Halden in March 2025.", response(assertion("Nora joined Halden", NORA)))
    assert not cset.candidates and kinds(report) == ["grounding-failure"]
    cset, report = run("Nora Vance joined Halden in March 2025.",
                       response(assertion("Nora Vance joined Halden", [("employee", "N. Vance", "person"), ("employer", "Halden", "organization")])))
    assert kinds(report) == ["grounding-failure"]


def test_an_ambiguous_span_needs_an_occurrence():
    text = "Nora Vance joined Halden. Later: Nora Vance joined Halden."
    cset, report = run(text, response(assertion("Nora Vance joined Halden", NORA)))
    assert not cset.candidates and kinds(report) == ["ambiguous-span"]
    cset, report = run(text, response(assertion("Nora Vance joined Halden", NORA, evidence_occurrence=2)))
    assert cset.candidates[0].passage.start == text.rindex("Nora Vance joined Halden")
    cset, report = run(text, response(assertion("Nora Vance joined Halden", NORA, evidence_occurrence=3)))
    assert kinds(report) == ["ambiguous-span"]


@pytest.mark.parametrize("participants, flagged", [
    ([("employee", "She", "person"), ("employer", "Halden", "organization")], False),
    ([("employee", "she", "person"), ("employer", "Halden", "organization")], False),
    ([("employee", "Nora Vance", "person"), ("employer", "Halden", "organization")], True),  # the model says vague
])
def test_pronouns_and_vague_references_are_never_resolved(participants, flagged):
    text = "Nora Vance is great. she joined Halden in March. She joined Halden."
    a = assertion("She joined Halden" if participants[0][1] == "She" else ("she joined Halden" if participants[0][1] == "she"
                                                                          else "Nora Vance is great"), participants)
    if flagged:
        a["participants"][0]["is_pronoun_or_vague"] = True
    cset, report = run(text, response(a))
    assert not cset.candidates and kinds(report) == ["ambiguous-reference"]


def test_first_person_needs_a_known_author():
    a = assertion("I joined Halden in June 2024", [("employee", "I", "person"), ("employer", "Halden", "organization")],
                  times=[("June 2024", "start")])
    assert run("I joined Halden in June 2024.", response(a))[0].candidates
    cset, report = run("I joined Halden in June 2024.", response(a), author=None)
    assert not cset.candidates and kinds(report) == ["ambiguous-reference"]


def test_certainty_is_never_kept_against_a_hedge():
    text = "Apparently Nora Vance joined Halden in March 2025."
    cset, report = run(text, response(assertion(text.rstrip("."), NORA, times=[("March 2025", "start")])))
    assert cset.candidates[0].commitment == "unknown"
    assert [f["kind"] for f in report.flags] == ["commitment-downgraded"]
    cset, _ = run(text, response(assertion(text.rstrip("."), NORA, times=[("March 2025", "start")], commitment="probable")))
    assert cset.candidates[0].commitment == "probable"   # an honest hedge is kept as it is
    text = "I think Nora Vance works at Halden."             # the hedge is outside the quoted evidence
    cset, _ = run(text, response(assertion("Nora Vance works at Halden", NORA)))
    assert cset.candidates[0].commitment == "unknown"


def test_polarity_and_modality_must_agree_with_the_evidence():
    cset, report = run("Nora Vance does not work at Halden.", response(assertion("Nora Vance does not work at Halden", NORA)))
    assert not cset.candidates and kinds(report) == ["cue-conflict"]
    cset, report = run("Nora Vance will join Halden in May.", response(assertion("Nora Vance will join Halden in May", NORA)))
    assert not cset.candidates and kinds(report) == ["cue-conflict"]
    text = "Correction: Nora Vance joined Halden in April 2025, not March."
    cset, report = run(text, response(assertion("Nora Vance joined Halden in April 2025, not March", NORA,
                                                times=[("April 2025", "start")])))
    assert cset.candidates and "cue-conflict" not in kinds(report)       # a contrast is not a denial
    cset, _ = run("Nora Vance does not work at Halden.",
                  response(assertion("Nora Vance does not work at Halden", NORA, polarity="negative")))
    assert cset.candidates[0].polarity == "negative"


def test_forwarded_text_is_forwarded_whatever_the_model_says():
    text = "FYI.\n---- Forwarded message ----\nFrom: Dana Okoro\nNora Vance joined Halden in March 2025."
    ev = "Nora Vance joined Halden in March 2025"
    said_direct = {"mode": "direct", "claimant": "Dana Okoro", "claimant_kind": "person", "via": []}
    cset, report = run(text, response(assertion(ev, NORA, times=[("March 2025", "start")], attribution=said_direct)))
    (c,) = cset.candidates
    assert (c.attribution.mode, c.attribution.asserted_by) == ("forwarded", "Dana Okoro")
    assert [f["kind"] for f in report.flags] == ["mode-forced-forwarded"]
    # the header names a sender but not what kind of entity it is: not assumed to be a person
    cset, report = run(text, response(assertion(ev, NORA, times=[("March 2025", "start")])))
    assert not cset.candidates and kinds(report) == ["claimant-kind-not-representable"]
    other = {"mode": "forwarded", "claimant": "Nora Vance", "claimant_kind": "person", "via": []}
    cset, report = run(text, response(assertion(ev, NORA, times=[("March 2025", "start")], attribution=other)))
    assert not cset.candidates and kinds(report) == ["cue-conflict"]


def test_claimants_must_be_in_the_text_and_representable():
    text = "According to Dana Okoro, Nora Vance joined Halden in March 2025."
    reported = {"mode": "reported", "claimant": "Dana Okoro", "claimant_kind": "person", "via": []}
    (c,) = run(text, response(assertion("Nora Vance joined Halden in March 2025", NORA, attribution=reported)))[0].candidates
    assert (c.attribution.mode, c.attribution.asserted_by) == ("reported", "Dana Okoro")
    for claimant, kind, outcome in (("Dana Okoro", "organization", "claimant-kind-not-representable"),
                                    ("Dana Okoro", "unclassified", "claimant-kind-not-representable"),
                                    ("Reuters", "organization", "grounding-failure"),
                                    ("She", "person", "ambiguous-reference")):
        at = {"mode": "reported", "claimant": claimant, "claimant_kind": kind, "via": []}
        cset, report = run(text, response(assertion("Nora Vance joined Halden in March 2025", NORA, attribution=at)))
        assert not cset.candidates and kinds(report) == [outcome], claimant


def test_a_correction_needs_exactly_one_target():
    first = "Nora Vance joined Halden in March 2025."
    earlier_a, _ = run(first, response(assertion(first.rstrip("."), NORA, times=[("March 2025", "start")])))
    fix_text = "Correction: Nora Vance joined Halden in April 2025, not March."
    fix = assertion("Nora Vance joined Halden in April 2025, not March", NORA, times=[("April 2025", "start")],
                    correction={"kind": "corrects", "cue": "Correction:", "earlier_statement": None})
    (c,) = run(fix_text, response(fix), prior=(earlier_a,))[0].candidates
    assert [(r.kind, r.target) for r in c.relations] == [("corrects", earlier_a.candidates[0].id)]
    cset, report = run(fix_text, response(fix))                                      # no earlier statement
    assert not cset.candidates and kinds(report) == ["correction-target-unresolved"]
    other_text = "Nora Vance joined Halden in February 2025."
    earlier_b, _ = run(other_text, response(assertion(other_text.rstrip("."), NORA, times=[("February 2025", "start")])))
    cset, report = run(fix_text, response(fix), prior=(earlier_a, earlier_b))     # two possible targets
    assert not cset.candidates and kinds(report) == ["correction-target-unresolved"]


def test_inferred_assertions_and_reported_problems_are_explicit():
    text = "Our new CFO starts Monday."
    a = assertion("Our new CFO starts Monday", [("employee", "CFO", "person"), ("employer", "Halden", "organization")])
    a["basis"] = "inferred"
    cset, report = run(text, response(a, problems=[{"kind": "ambiguous-reference", "evidence": "Our new CFO",
                                                    "detail": "nobody is named"}]))
    assert not cset.candidates and sorted(kinds(report)) == ["ambiguous-reference", "inferred-not-admissible"]
    cset, report = run("Can we move the meeting to Friday?", response(outcome="no-relevant-assertion"))
    assert not cset.candidates and kinds(report) == ["no-relevant-assertion"]


def test_statements_carry_their_predicate_and_since_is_never_a_start():
    text = "Halden Holdings owns Pellwick."
    a = assertion("Halden Holdings owns Pellwick", [("subject", "Halden Holdings", "organization"), ("object", "Pellwick", "organization")],
                  relation="statement", predicate="owns")
    (c,) = run(text, response(a))[0].candidates
    assert c.values == (("predicate-text", "owns"),)
    text = "Nora Vance has worked at Halden since March 2025."
    cset, report = run(text, response(assertion(text.rstrip("."), NORA, times=[("March 2025", "start")])))
    assert not cset.candidates and kinds(report) == ["validation"] and "since-as-start" in report.outcomes[0]["detail"]


def test_extraction_is_deterministic_and_never_mutates_the_response():
    text = "Nora Vance joined Halden in March 2025."
    resp = response(assertion(text.rstrip("."), NORA, times=[("March 2025", "start")]))
    before = copy.deepcopy(resp)
    a, b = run(text, resp), run(text, json.dumps(resp))
    assert a[0] == b[0] and resp == before


def test_a_present_tense_verb_holds_at_the_moment_it_was_written():
    text = "Ilsa Moreno reports to Teo Brandt."
    a = assertion("Ilsa Moreno reports to Teo Brandt", [("report", "Ilsa Moreno", "person"), ("manager", "Teo Brandt", "person")],
                  relation="reporting", times=[("reports", "holds-at")])
    (c,) = run(text, response(a))[0].candidates
    assert (c.times[0].earliest, c.times[0].latest, c.times[0].precision) == (SAID, SAID, "instant")
    cset, report = run("Ilsa Moreno reported to Teo Brandt.", response(
        assertion("Ilsa Moreno reported to Teo Brandt", [("report", "Ilsa Moreno", "person"), ("manager", "Teo Brandt", "person")],
                  relation="reporting", times=[("reported", "holds-at")])))
    assert cset.candidates[0].times[0].precision == "unknown" and [f["kind"] for f in report.flags] == ["unreadable-time"]
