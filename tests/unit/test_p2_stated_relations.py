"""Phase 8D, P2: "my" is the author only where the words state a relation to a named person."""

from datetime import datetime, timezone

import pytest

from gupi.formation import form as policy
from gupi.formation.model_candidate import RESPONSE_FORMAT, ModelCandidateV1
from gupi.records import Observation

WHEN = datetime(2023, 5, 8, tzinfo=timezone.utc)
DIRECT = {"mode": "direct", "claimant": None, "claimant_kind": None, "via": []}


def p(role, text, kind="person", vague=False):
    return {"role": role, "text": text, "kind": kind, "is_pronoun_or_vague": vague}


def kin(evidence, name, predicate, my="My", **over):
    return {"evidence": evidence, "relation": "statement", "participants": [p("subject", my), p("object", name)], "predicate": predicate,
            "times": [], "polarity": "positive", "modality": "actual", "commitment": "certain", "basis": "explicit", "attribution": DIRECT} | over


def boss(evidence, name, **over):
    return {"evidence": evidence, "relation": "reporting", "participants": [p("report", "My"), p("manager", name)], "times": [],
            "polarity": "positive", "modality": "actual", "commitment": "certain", "basis": "explicit", "attribution": DIRECT} | over


def read(message, *assertions, author="p:juno", prior=()):
    obs = Observation("src:t", "k", message, WHEN, "s1", author)
    return ModelCandidateV1().extract(obs, prior=prior, response={"format": RESPONSE_FORMAT, "outcome": "assertions", "assertions": list(assertions), "problems": []})


def stopped(report):
    return [o["kind"] for o in report.outcomes]


@pytest.mark.parametrize("message, evidence, name, noun", [
    ("My sister Kate lives in Bristol.", "My sister Kate", "Kate", "sister"),
    ("My colleague James joined last year.", "My colleague James", "James", "colleague"),
    ("Yesterday my older brother Tom Reed called.", "my older brother Tom Reed", "Tom Reed", "brother"),
    ("I saw my best friend Ana.", "my best friend Ana", "Ana", "friend"),
])
def test_a_stated_relation_is_read(message, evidence, name, noun):
    cset, report = read(message, kin(evidence, name, noun, my=evidence.split()[0]))
    c = cset.candidates[0]
    assert not report.outcomes and {x.surface for x in c.participants} == {evidence.split()[0], name}
    assert dict(c.values)["predicate-text"] == noun and "stated-relation" in {f["kind"] for f in report.flags}
    assert policy.decide(c, [], {}).outcome == "formed"


def test_a_manager_is_a_typed_reporting_line():
    cset, report = read("My manager Alice works at Meridian.", boss("My manager Alice", "Alice"))
    c = cset.candidates[0]
    assert c.claim_type == "reporting" and {x.role: x.surface for x in c.participants} == {"report": "My", "manager": "Alice"}
    assert policy.decide(c, [], {}).outcome == "formed"


def test_the_my_cited_is_the_one_that_states_it():
    message = "My plan with my sister Kate is fine."
    cset, _ = read(message, kin("my sister Kate", "Kate", "sister", my="my"))
    assert message[cset.candidates[0].participants[0].start:][:13] == "my sister Kat"


@pytest.mark.parametrize("message, assertion", [
    ("My sister moved.", kin("My sister moved", "sister", "sister")),                       # no name
    ("My former manager Alice left.", boss("My former manager Alice", "Alice")),            # the relation has ended
    ("My late husband Tom sang.", kin("My late husband Tom", "Tom", "husband")),
    ("My ex-boyfriend Tom sang.", kin("My ex-boyfriend Tom", "Tom", "boyfriend")),
    ("My dog Luna ran.", kin("My dog Luna", "Luna", "dog")),                                # not a listed relation
    ("My sister Kate left.", kin("My sister Kate", "Kate", "brother")),                     # the words say otherwise
    ("My sister Kate met Tom.", kin("My sister Kate met Tom", "Tom", "sister")),            # the wrong person
    ("My friend Monday is here.", kin("My friend Monday", "Monday", "friend")),             # not a name
    ('Tom wrote "my sister Kate left".', kin("my sister Kate", "Kate", "sister", my="my")),  # quoted words
    ("My sister Kate left.", kin("My sister Kate", "Kate", "sister", relation="employment")),
])
def test_anything_less_than_a_stated_relation_still_stops(message, assertion):
    cset, report = read(message, assertion)
    assert not cset.candidates and stopped(report) in (["ambiguous-reference"], ["validation"])


@pytest.mark.parametrize("attribution", [
    {"mode": "reported", "claimant": "Bram", "claimant_kind": "person", "via": []},
    {"mode": "quoted", "claimant": None, "claimant_kind": None, "via": []},
    {"mode": "rumour", "claimant": None, "claimant_kind": None, "via": []},
])
def test_my_in_someone_elses_words_is_not_the_author(attribution):
    cset, report = read("Bram says my sister Kate left.", kin("my sister Kate", "Kate", "sister", my="my", attribution=attribution))
    assert not cset.candidates and stopped(report) == ["ambiguous-reference"]


def test_forwarded_text_is_not_the_author():
    message = "---- Forwarded message ----\nFrom: Bram\nMy sister Kate left."
    cset, report = read(message, kin("My sister Kate", "Kate", "sister"))
    assert not cset.candidates and stopped(report) == ["ambiguous-reference"]


def test_with_no_known_author_nothing_is_resolved():
    cset, report = read("My sister Kate left.", kin("My sister Kate", "Kate", "sister"), author=None)
    assert not cset.candidates and stopped(report) == ["ambiguous-reference"]


def test_the_model_saying_vague_is_respected():
    a = kin("My sister Kate", "Kate", "sister")
    a["participants"][0]["is_pronoun_or_vague"] = True
    cset, report = read("My sister Kate left.", a)
    assert not cset.candidates and stopped(report) == ["ambiguous-reference"]


def test_a_hedge_keeps_going_to_review():
    cset, _ = read("I think my sister Kate left.", kin("my sister Kate", "Kate", "sister", my="my"))
    c = cset.candidates[0]
    assert c.commitment == "unknown" and policy.decide(c, [], {}).outcome == "review"


def test_a_negated_relation_is_not_read_as_a_relation():
    cset, report = read("She is not my sister Kate.", kin("my sister Kate", "Kate", "sister", my="my"))
    assert not cset.candidates and stopped(report) == ["cue-conflict"]


def test_a_comma_form_is_read_but_a_reviewer_confirms_it():
    cset, _ = read("My sister, Kate, left.", kin("My sister, Kate", "Kate", "sister"))
    assert policy.decide(cset.candidates[0], [], {}).outcome == "review"


def test_two_relations_for_one_name_in_a_conversation_go_to_review():
    first, _ = read("My sister Kate left.", kin("My sister Kate", "Kate", "sister"))
    second, report = read("My colleague Kate left.", kin("My colleague Kate", "Kate", "colleague"), prior=(first,))
    assert "relation-name-conflict" in {f["kind"] for f in report.flags}
    assert policy.decide(second.candidates[0], [], {}).outcome == "review"


def test_two_words_for_one_relation_are_not_a_conflict():
    first, _ = read("My boss Alice left.", boss("My boss Alice", "Alice"))
    second, report = read("My manager Alice left.", boss("My manager Alice", "Alice"), prior=(first,))
    assert "relation-name-conflict" not in {f["kind"] for f in report.flags}
    assert policy.decide(second.candidates[0], [], {}).outcome == "formed"
