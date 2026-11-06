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
    assert c.attribution.asserted_by_kind == "person"
    # the header names a sender but not what kind of entity it is: an unknown-kind claimant, not a person
    cset, report = run(text, response(assertion(ev, NORA, times=[("March 2025", "start")])))
    (c,) = cset.candidates
    assert (c.attribution.asserted_by, c.attribution.asserted_by_kind, c.attribution.mode) == ("Dana Okoro", "unknown", "forwarded")
    other = {"mode": "forwarded", "claimant": "Nora Vance", "claimant_kind": "person", "via": []}
    cset, report = run(text, response(assertion(ev, NORA, times=[("March 2025", "start")], attribution=other)))
    assert not cset.candidates and kinds(report) == ["cue-conflict"]


def test_claimants_must_be_in_the_text_and_representable():
    text = "According to Dana Okoro, Nora Vance joined Halden in March 2025."
    reported = {"mode": "reported", "claimant": "Dana Okoro", "claimant_kind": "person", "via": []}
    (c,) = run(text, response(assertion("Nora Vance joined Halden in March 2025", NORA, attribution=reported)))[0].candidates
    assert (c.attribution.mode, c.attribution.asserted_by) == ("reported", "Dana Okoro")
    assert c.attribution.asserted_by_kind == "person"
    for claimant, kind, want in (("Dana Okoro", "organization", "organisation"),     # format 1 vocabulary, mapped
                                 ("Dana Okoro", "unclassified", "unknown")):
        at = {"mode": "reported", "claimant": claimant, "claimant_kind": kind, "via": []}
        r1 = dict(response(assertion("Nora Vance joined Halden in March 2025", NORA, attribution=at)), format="gupi.model-response/1")
        (c,) = run(text, r1)[0].candidates
        assert c.attribution.asserted_by_kind == want
    for claimant, kind, outcome in (("Reuters", "organisation", "grounding-failure"),
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
    # D3 (format 1.1): no single target -> a null target, which formation always reviews; never a guess
    (c,) = run(fix_text, response(fix))[0].candidates                               # no earlier statement
    assert [(r.kind, r.target) for r in c.relations] == [("corrects", None)]
    other_text = "Nora Vance joined Halden in February 2025."
    earlier_b, _ = run(other_text, response(assertion(other_text.rstrip("."), NORA, times=[("February 2025", "start")])))
    cset, report = run(fix_text, response(fix), prior=(earlier_a, earlier_b))     # two possible targets
    assert [(r.kind, r.target) for r in cset.candidates[0].relations] == [("corrects", None)]
    assert [f["kind"] for f in report.flags] == ["correction-target-unresolved"]
    contra = dict(fix, correction={"kind": "contradicts", "cue": "Correction:", "earlier_statement": None})
    cset, report = run(fix_text, response(contra))                                 # a contradiction must name one
    assert not cset.candidates and kinds(report) == ["correction-target-unresolved"]


def test_a_correction_whose_subject_is_a_pronoun_is_never_resolved():
    """D3, pronoun case: "Sorry, she joined in April" names neither its subject nor its target. No candidate is
    produced (the pronoun is not resolved), so no target can be guessed and no earlier claim is touched."""
    first = "Nora Vance joined Halden in March 2025."
    earlier, _ = run(first, response(assertion(first.rstrip("."), NORA, times=[("March 2025", "start")])))
    text = "Sorry, she joined Halden in April 2025."
    fix = assertion("she joined Halden in April 2025", [("employee", "she", "person"), ("employer", "Halden", "organization")],
                    times=[("April 2025", "start")], correction={"kind": "corrects", "cue": "Sorry,", "earlier_statement": None})
    cset, report = run(text, response(fix), prior=(earlier,))
    assert not cset.candidates and kinds(report) == ["ambiguous-reference"]


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


def test_format_1_1_output_and_both_response_formats():
    text = "According to Halden Press, Nora Vance joined Halden in March 2025."
    at11 = {"mode": "reported", "claimant": "Halden Press", "claimant_kind": "organisation", "via": []}
    r11 = dict(response(assertion("Nora Vance joined Halden in March 2025", NORA, attribution=at11)), format="gupi.model-response/1.1")
    cset, _ = run(text, r11)
    assert cset.ir_version == "gupi.candidate/1.1" and cset.candidates[0].attribution.asserted_by_kind == "organisation"
    bad = dict(r11, assertions=[dict(r11["assertions"][0], attribution=dict(at11, claimant_kind="organization"))])
    assert kinds(run(text, bad)[1]) == ["invalid-model-output"]                  # each format has its own vocabulary
    old = dict(response(assertion("Nora Vance joined Halden in March 2025", NORA,
                                  attribution=dict(at11, claimant_kind="organization"))), format="gupi.model-response/1")
    assert run(text, old)[0].candidates[0].attribution.asserted_by_kind == "organisation"


# --- Phase 8C: a word is not its letters -----------------------------------------------------------------------

def _first_person(evidence, **over):
    return {"format": RESPONSE_FORMAT, "outcome": "assertions", "problems": [], "assertions": [{
        "evidence": evidence, "relation": "statement", "predicate": "met", "times": [], "polarity": "positive", "modality": "actual",
        "commitment": "certain", "basis": "explicit", "participants": [{"role": "subject", "text": "I", "kind": "person", "is_pronoun_or_vague": False}],
        "attribution": {"mode": "direct", "claimant": None, "claimant_kind": None, "via": []}} | over]}


def _read(message, response):
    return ModelCandidateV1().extract(Observation("src:t", "k", message, datetime(2023, 5, 8, tzinfo=timezone.utc), "s", "p:juno"), response=response)


def test_capital_i_inside_a_word_is_not_a_second_i():
    cset, report = _read("I met them in Italy.", _first_person("I met them in Italy"))
    assert [p.start for p in cset.candidates[0].participants] == [0] and not report.outcomes


def test_two_uses_of_i_by_the_author_are_one_referent():
    cset, _ = _read("I said I met them.", _first_person("I said I met them"))
    assert [p.start for p in cset.candidates[0].participants] == [0]


def test_a_second_i_in_someone_elses_words_still_stops():
    reported = {"mode": "reported", "claimant": "Bram", "claimant_kind": "person", "via": []}
    cset, report = _read("Bram said I met I.", _first_person("Bram said I met I", attribution=reported))
    assert not cset.candidates and report.outcomes[0]["kind"] == "ambiguous-span"


def test_a_repeated_name_still_stops():
    named = [{"role": "subject", "text": "Bram", "kind": "person", "is_pronoun_or_vague": False}]
    cset, report = _read("Bram met Bram.", _first_person("Bram met Bram", participants=named))
    assert not cset.candidates and report.outcomes[0]["kind"] == "ambiguous-span"


def test_a_name_only_inside_longer_words_is_unchanged():
    named = [{"role": "subject", "text": "Bram", "kind": "person", "is_pronoun_or_vague": False}]
    cset, _ = _read("Bramley met them.", _first_person("Bramley met them", participants=named))
    assert cset.candidates[0].participants[0].surface == "Bram"      # as before: stopping this is a separate question


def test_evidence_spans_are_not_relaxed():
    cset, report = _read("I met them. I met them.", _first_person("I met them"))
    assert not cset.candidates and report.outcomes[0]["kind"] == "ambiguous-span"
