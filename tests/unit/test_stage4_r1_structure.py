"""R1 (Phase 7B Stage 4): a grounded statement whose roles do not state the passage's relation is sent to review,
never formed by the policy. Synthetic, developer-authored fixtures: no evaluation passage or answer."""

import pytest

from gupi.formation.fidelity import statement_problems
from gupi.formation.form import decide

from test_model_candidate import NORA, assertion, response, run


def statement(text, evidence, participants, predicate, object_text=None, **kw):
    extra = {"object_text": object_text} if object_text else {}
    cset, report = run(text, response(assertion(evidence, participants, relation="statement", predicate=predicate,
                                                **extra, **kw)))
    assert report.outcomes == [], report.outcomes
    (c,) = cset.candidates
    return c


def outcome(c, approvals=None):
    return decide(c, [], approvals or {})


ORG = "organization"


# --- the failure classes are blocked -----------------------------------------------------------------------

def test_object_participant_separated_from_predicate_goes_to_review():
    # the X3-27/28 class: the qualifier linking the object participant ("an inquiry into") is outside the roles
    c = statement("Brackwater Audit has opened an inquiry into Lena Ostrow.",
                  "Brackwater Audit has opened an inquiry into Lena Ostrow",
                  [("subject", "Brackwater Audit", ORG), ("object", "Lena Ostrow", "person")],
                  "has opened", "an inquiry")
    d = outcome(c)
    assert d.outcome == "review" and "statement structure not verified" in d.reason
    assert "'an inquiry into' stands between them" in d.reason


def test_object_participant_inside_object_text_goes_to_review():
    # the X3-19 class: "run by the same crew as Y" stored as "run by Y"
    c = statement("The KESTREL-4 cluster is run by the same crew as the GREY HERON set.",
                  "The KESTREL-4 cluster is run by the same crew as the GREY HERON set",
                  [("subject", "KESTREL-4", ORG), ("object", "GREY HERON", ORG)],
                  "is run by", "the same crew as the GREY HERON set")
    problems = statement_problems(c)
    assert any("lies inside the object text" in p for p in problems)
    assert any("not the direct object" in p for p in problems)
    assert outcome(c).outcome == "review"


def test_possessor_as_object_goes_to_review():
    c = statement("The port authority has suspended Fenwick Shipping's dock licence.",
                  "The port authority has suspended Fenwick Shipping's dock licence",
                  [("subject", "port authority", ORG), ("object", "Fenwick Shipping", ORG)], "has suspended")
    assert any("possessor" in p for p in statement_problems(c)) and outcome(c).outcome == "review"


def test_paraphrased_predicate_with_an_object_cannot_be_checked():
    c = statement("Halden Holdings bought Pellwick.", "Halden Holdings bought Pellwick",
                  [("subject", "Halden Holdings", ORG), ("object", "Pellwick", ORG)], "acquired")
    assert outcome(c).outcome == "review" and "does not occur in the passage" in outcome(c).reason


def test_object_before_the_predicate_goes_to_review():
    c = statement("Pellwick was bought by Halden Holdings.", "Pellwick was bought by Halden Holdings",
                  [("subject", "Halden Holdings", ORG), ("object", "Pellwick", ORG)], "was bought by")
    assert outcome(c).outcome == "review"


# --- correct statements still form -------------------------------------------------------------------------

@pytest.mark.parametrize("text, participants, predicate, object_text", [
    ("Halden Holdings owns Pellwick.", [("subject", "Halden Holdings", ORG), ("object", "Pellwick", ORG)], "owns", None),
    ("Brackwater Audit accessed the Corrin Water network.",
     [("subject", "Brackwater Audit", ORG), ("object", "Corrin Water network", ORG)], "accessed", None),
    ("Halden Holdings has opened an inquiry into Pellwick.",
     [("subject", "Halden Holdings", ORG), ("object", "Pellwick", ORG)], "has opened an inquiry into", None),
    ("The port authority has suspended Fenwick Shipping's dock licence.", [("subject", "port authority", ORG)],
     "has suspended", "Fenwick Shipping's dock licence"),
    ("Kim Arden retired.", [("subject", "Kim Arden", "person")], "retired", None),
])
def test_faithful_statements_form(text, participants, predicate, object_text):
    c = statement(text, text.rstrip("."), participants, predicate, object_text)
    assert statement_problems(c) == []
    d = outcome(c)
    assert d.outcome == "formed" and d.decided_by == "formation:v1"


def test_a_reviewer_can_still_approve_an_unverified_structure():
    c = statement("Brackwater Audit has opened an inquiry into Lena Ostrow.",
                  "Brackwater Audit has opened an inquiry into Lena Ostrow",
                  [("subject", "Brackwater Audit", ORG), ("object", "Lena Ostrow", "person")], "has opened", "an inquiry")
    d = outcome(c, {c.id: "reviewer-a"})
    assert d.outcome == "formed" and d.decided_by == "reviewer-a" and "approved by review" in d.reason


def test_typed_claims_are_not_affected():
    cset, _ = run("Nora Vance joined Halden in March 2025.",
                  response(assertion("Nora Vance joined Halden in March 2025", NORA, times=[("March 2025", "start")])))
    (c,) = cset.candidates
    assert statement_problems(c) == [] and outcome(c).outcome == "formed"


def test_other_safeguards_keep_their_order():
    # a planned statement is still withheld (modality comes first), not sent to review by R1
    c = statement("Halden Holdings might open an inquiry into Lena Ostrow.",
                  "Halden Holdings might open an inquiry into Lena Ostrow",
                  [("subject", "Halden Holdings", ORG), ("object", "Lena Ostrow", "person")], "might open", "an inquiry",
                  modality="planned", commitment="possible")
    assert outcome(c).outcome == "withheld"


def test_the_predicate_is_matched_as_whole_words():
    # review fix: "owns" inside "disowns" must not verify "X owns Y"
    c = statement("Halden disowns Pellwick.", "Halden disowns Pellwick",
                  [("subject", "Halden", ORG), ("object", "Pellwick", ORG)], "owns")
    assert outcome(c).outcome == "review" and "does not occur in the passage" in outcome(c).reason


@pytest.mark.parametrize("text, predicate, obj", [
    ("Halden acquired Pellwick.", "acquired", "Pellwick"),
    ("Halden sued Pellwick.", "sued", "Pellwick"),
    ("Halden met with Pellwick.", "met with", "Pellwick"),
    ("Halden has partnered with Pellwick.", "has partnered with", "Pellwick"),
    ("Halden is a subsidiary of Pellwick.", "is a subsidiary of", "Pellwick"),
    ("Halden invested in Pellwick.", "invested in", "Pellwick"),
    ("Halden Acquired Pellwick.", "acquired", "Pellwick"),
    ("Halden acquired  the\nPellwick group.", "acquired", "Pellwick group"),
    ("Halden acquired Pellwick in May 2025.", "acquired", "Pellwick"),
    ("Halden, the regulator, fined Pellwick on Monday.", "fined", "Pellwick"),
    ("Halden has sued and fined Pellwick.", "fined", "Pellwick"),
    ("Halden acquired an 80% stake in Pellwick.", "acquired an 80% stake in", "Pellwick"),
])
def test_common_valid_constructions_form(text, predicate, obj):
    c = statement(text, text.rstrip("."), [("subject", "Halden", ORG), ("object", obj, ORG)], predicate)
    assert statement_problems(c) == [] and outcome(c).outcome == "formed"


@pytest.mark.parametrize("text, predicate, obj", [
    ("Halden lives in Pellwick.", "lives", "Pellwick"),                       # preposition left out: conservative
    ("Halden acquired an 80% stake in Pellwick.", "acquired", "Pellwick"),    # "acquired Pellwick" overstates
    ("Halden met Pellwick's chair.", "met", "Pellwick"),                      # possessor
])
def test_constructions_deliberately_sent_to_review(text, predicate, obj):
    c = statement(text, text.rstrip("."), [("subject", "Halden", ORG), ("object", obj, ORG)], predicate)
    assert outcome(c).outcome == "review"
