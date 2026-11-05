"""R3 (Phase 7B Stage 4): a fact embedded in an allegation is never admitted as an unqualified fact. It keeps (or
takes) the alleger's attribution, loses `certain`, and goes to review. Synthetic, developer-authored fixtures."""

from gupi.formation.form import decide

from test_model_candidate import assertion, response, run

TEXT = "The lawsuit alleges that Corvane Freight's finance director, Ilse Marrow, hid losses from auditors."
CLAUSE = TEXT.rstrip(".")
ILSE = [("employee", "Ilse Marrow", "person"), ("employer", "Corvane Freight", "organization")]
LAWSUIT = {"mode": "reported", "claimant": "The lawsuit", "claimant_kind": "unknown", "via": []}


def alleged_statement(**kw):
    return assertion(CLAUSE, [("subject", "Ilse Marrow", "person")], relation="statement", predicate="hid",
                     object_text="losses from auditors", attribution=LAWSUIT, allegation=True, **kw)


def employment(**kw):
    return assertion("Corvane Freight's finance director, Ilse Marrow", ILSE, title="finance director", **kw)


def flags(report, kind):
    return [f for f in report.flags if f["kind"] == kind]


def by_type(cset):
    return {c.claim_type: c for c in cset.candidates}


def test_an_employment_inside_an_allegation_takes_the_allegers_attribution_and_goes_to_review():
    cset, report = run(TEXT, response(alleged_statement(), employment()))
    emp = by_type(cset)["employment"]
    assert emp.commitment == "unknown"
    assert (emp.attribution.mode, emp.attribution.asserted_by) == ("reported", "The lawsuit")
    assert flags(report, "allegation-inherited")
    d = decide(emp, [], {})
    assert d.outcome == "review" and "hedged by the source (unknown)" in d.reason
    assert decide(by_type(cset)["statement"], [], {}).outcome == "review"   # the allegation itself, as before


def test_a_claimant_the_model_gave_is_kept():
    own = {"mode": "reported", "claimant": "Corvane Freight", "claimant_kind": "organisation", "via": []}
    cset, _ = run(TEXT, response(alleged_statement(), employment(attribution=own)))
    emp = by_type(cset)["employment"]
    assert emp.attribution.asserted_by == "Corvane Freight" and emp.commitment == "unknown"


def test_an_allegation_cue_works_even_when_the_model_marks_nothing():
    text = "Ilse Marrow, the finance director at Corvane Freight, is accused of hiding losses."
    cset, report = run(text, response(assertion("Ilse Marrow, the finance director at Corvane Freight", ILSE,
                                                title="finance director")))
    (emp,) = cset.candidates
    assert emp.commitment == "unknown" and flags(report, "allegation-context")
    assert decide(emp, [], {}).outcome == "review"


def test_a_less_than_certain_commitment_is_not_raised_or_changed():
    cset, _ = run(TEXT, response(alleged_statement(), employment(commitment="probable")))
    assert by_type(cset)["employment"].commitment == "probable"


def test_facts_outside_the_allegation_form_normally():
    text = "The lawsuit alleges fraud. Ilse Marrow joined Corvane Freight in May 2024."
    cset, report = run(text, response(assertion("Ilse Marrow joined Corvane Freight in May 2024", ILSE,
                                                times=[("May 2024", "start")])))
    (emp,) = cset.candidates
    assert emp.commitment == "certain" and emp.attribution.mode == "direct"
    assert not flags(report, "allegation-context") and decide(emp, [], {}).outcome == "formed"


def test_time_and_provenance_survive_the_inheritance():
    text = "The lawsuit alleges that Ilse Marrow joined Corvane Freight in May 2024 and hid losses."
    stmt = assertion(text.rstrip("."), [("subject", "Ilse Marrow", "person")], relation="statement",
                     predicate="hid", object_text="losses", attribution=LAWSUIT, allegation=True)
    emp = assertion("Ilse Marrow joined Corvane Freight in May 2024", ILSE, times=[("May 2024", "start")])
    cset, _ = run(text, response(stmt, emp))
    c = by_type(cset)["employment"]
    (t,) = c.times
    assert (t.kind, t.earliest.date().isoformat(), t.latest.date().isoformat()) == ("start", "2024-05-01", "2024-06-01")
    assert c.passage.text == "Ilse Marrow joined Corvane Freight in May 2024"
    assert c.attribution.via == ("p:ivo-marsh",)  # the author passed it on, as for any reported claim
