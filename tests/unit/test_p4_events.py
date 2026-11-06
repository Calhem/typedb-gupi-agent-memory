"""Phase 8D, P4: reading one-time events. Pure: no database."""

from datetime import datetime, timezone

import pytest

from gupi.formation import form as policy
from gupi.formation.candidate import EVENT_TYPE
from gupi.formation.model_candidate import RESPONSE_FORMAT, RESPONSE_FORMAT_1_1, ModelCandidateV1
from gupi.formation.validate import Unmappable, occurrence
from gupi.records import Observation

WHEN = datetime(2023, 5, 8, 13, 0, tzinfo=timezone.utc)
DIRECT = {"mode": "direct", "claimant": None, "claimant_kind": None, "via": []}
ME = {"role": "subject", "text": "I", "kind": "person", "is_pronoun_or_vague": False}


def event(evidence, predicate, *times, participants=(ME,), **over):
    return {"evidence": evidence, "relation": "event", "participants": list(participants), "predicate": predicate,
            "times": [{"text": t, "kind": k} for t, k in times], "polarity": "positive", "modality": "actual", "commitment": "certain",
            "basis": "explicit", "attribution": DIRECT} | over


def read(message, a, fmt=RESPONSE_FORMAT):
    obs = Observation("src:t", "k", message, WHEN, "s1", "p:juno")
    return ModelCandidateV1().extract(obs, response={"format": fmt, "outcome": "assertions", "assertions": [a], "problems": []})


def formed(message, a):
    cset, report = read(message, a)
    assert not report.outcomes, report.outcomes
    return cset.candidates[0], policy.decide(cset.candidates[0], [], {})


@pytest.mark.parametrize("message, evidence, phrase, basis", [
    ("I moved to Bristol in 2021.", "I moved to Bristol in 2021", "in 2021", "stated"),
    ("I moved to Bristol on 3 May 2022.", "I moved to Bristol on 3 May 2022", "on 3 May 2022", "stated"),
    ("I moved to Bristol last week.", "I moved to Bristol last week", "last week", "derived"),
    ("I moved to Bristol yesterday.", "I moved to Bristol yesterday", "yesterday", "derived"),
])
def test_a_dated_event_is_formed_with_its_own_window(message, evidence, phrase, basis):
    c, d = formed(message, event(evidence, "moved to", (phrase, "holds-at"), object_text="Bristol"))
    earliest, latest, read_basis, precision = occurrence(c)
    assert d.outcome == "formed" and c.claim_type == EVENT_TYPE
    assert earliest < latest <= WHEN and read_basis == basis and precision in ("day", "month", "year", "instant")


def test_a_week_is_a_window_not_a_guessed_day():
    c, _ = formed("I moved to Bristol last week.", event("I moved to Bristol last week", "moved to", ("last week", "holds-at")))
    earliest, latest, _, _ = occurrence(c)
    assert (latest - earliest).days >= 7


def test_no_date_stays_no_date():
    c, d = formed("I moved to Bristol.", event("I moved to Bristol", "moved to"))
    assert occurrence(c) == (None, None, None, None) and d.outcome == "formed"


def test_an_unreadable_date_waits_for_a_reviewer():
    c, d = formed("I moved to Bristol during the great storm.",
                  event("I moved to Bristol during the great storm", "moved to", ("during the great storm", "holds-at")))
    assert d.outcome == "review"


@pytest.mark.parametrize("predicate", ["was", "lives in", "worked at", "has", "loved", "is"])
def test_a_state_is_never_an_event(predicate):
    message = f"I {predicate} Bristol in 2021."
    cset, report = read(message, event(f"I {predicate} Bristol in 2021", predicate, ("2021", "holds-at")))
    assert not cset.candidates and report.outcomes[0]["kind"] == "cue-conflict"


def test_something_dated_after_the_message_has_not_happened():
    cset, report = read("I moved to Bristol next month.", event("I moved to Bristol next month", "moved to", ("next month", "holds-at")))
    assert not cset.candidates and report.outcomes[0]["kind"] == "cue-conflict"


@pytest.mark.parametrize("times", [[("2021", "start")], [("2021", "end")], [("2021", "holds-since")], [("2021", "holds-at"), ("2022", "holds-at")]])
def test_an_event_has_one_moment_not_a_span(times):
    message = "I moved to Bristol in 2021 or 2022."
    cset, _ = read(message, event("I moved to Bristol in 2021 or 2022", "moved to", *times))
    assert policy.decide(cset.candidates[0], [], {}).outcome == "withheld"
    with pytest.raises(Unmappable):
        occurrence(cset.candidates[0])


def test_every_protection_still_applies_to_an_event():
    plan, _ = read("I might move to Bristol.", event("I might move to Bristol", "move to", modality="hypothetical", commitment="possible"))
    assert policy.decide(plan.candidates[0], [], {}).outcome == "withheld"
    hedged, _ = read("I think I moved to Bristol in 2021.", event("I moved to Bristol in 2021", "moved to", ("2021", "holds-at")))
    assert policy.decide(hedged.candidates[0], [], {}).outcome == "review"
    inferred, report = read("I moved to Bristol.", event("I moved to Bristol", "moved to", basis="inferred"))
    assert not inferred.candidates and report.outcomes[0]["kind"] == "inferred-not-admissible"
    negated, report = read("I never moved to Bristol.", event("I never moved to Bristol", "moved to"))
    assert not negated.candidates and report.outcomes[0]["kind"] == "cue-conflict"
    she = dict(ME, text="She", is_pronoun_or_vague=True)
    pronoun, report = read("She moved to Bristol.", event("She moved to Bristol", "moved to", participants=(she,)))
    assert not pronoun.candidates and report.outcomes[0]["kind"] == "ambiguous-reference"


def test_a_reported_event_keeps_who_said_it():
    reported = {"mode": "reported", "claimant": "Bram", "claimant_kind": "person", "via": []}
    cset, _ = read("Bram says Kate moved to Bristol in 2021.", event("Kate moved to Bristol in 2021", "moved to", ("2021", "holds-at"),
                   participants=(dict(ME, text="Kate"),), attribution=reported))
    assert cset.candidates[0].attribution.asserted_by == "Bram" and cset.candidates[0].attribution.mode == "reported"


def test_an_earlier_format_cannot_introduce_an_event():
    cset, report = read("I moved to Bristol.", event("I moved to Bristol", "moved to"), fmt=RESPONSE_FORMAT_1_1)
    assert not cset.candidates and report.outcomes[0]["kind"] == "invalid-model-output"


def test_an_implicit_participant_is_not_invented():
    cset, report = read("Moved to Bristol in 2021.", event("Moved to Bristol in 2021", "Moved to", ("2021", "holds-at")))
    assert not cset.candidates and report.outcomes[0]["kind"] == "grounding-failure"
