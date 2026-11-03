"""Phase 6A: the memory-candidate representation and its structural validation (docs/formation/candidate-ir.md)."""

import ast
import dataclasses
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from gupi import ids
from gupi.answering_v2 import classify
from gupi.extraction.contract import SchemaInfo
from gupi.formation.candidate import (
    Attribution, Candidate, CandidateSet, Participant, Passage, Relation, TimeEvidence, from_dict, to_dict,
)
from gupi.formation.validate import Unmappable, valid_time, validate
from gupi.records import Observation
from gupi.temporal import Answer, ValidTime


def d(y, m=1, day=1):
    return datetime(y, m, day, tzinfo=timezone.utc)


SAID = d(2025, 8, 20)
SCHEMA = SchemaInfo(
    frozenset({"person", "organization"}),
    {"employment": {"employee": frozenset({"person"}), "employer": frozenset({"organization"})},
     "identity": {"same": frozenset({"person"})}},
    {"employment": frozenset({"job-title"})})


def obs(text):
    return Observation("src:hr", "k1", text, SAID)


def at(text, phrase, nth=0):
    i = -1
    for _ in range(nth + 1):
        i = text.index(phrase, i + 1)
    return i, i + len(phrase)


def employment(text, times=(), **kw):
    """An employment candidate for a sentence naming Nora Vance and Halden."""
    o = obs(text)
    parts = (Participant("employee", "Nora Vance", *at(text, "Nora Vance"), "person"),
             Participant("employer", "Halden", *at(text, "Halden"), "organization"))
    c = Candidate("employment", Passage(o.id, 0, len(text), text), parts, (("job-title", "CTO"),), tuple(times), **kw)
    return o, c


def one(o, *candidates, extractor="test:v1"):
    return CandidateSet(o.id, ids.content_hash(o.content), extractor, tuple(candidates))


def codes(o, *candidates, schema=None):
    return sorted(i.code for i in validate(one(o, *candidates), o, schema))


def month(text, phrase, kind, y, m):
    nxt = d(y + m // 12, m % 12 + 1)
    return TimeEvidence(kind, phrase, *at(text, phrase), d(y, m), nxt, "month")


NOW = TimeEvidence("holds-at", "works", 0, 0, SAID, SAID, "instant")  # offsets fixed per sentence below


# --- "since" is not a start ------------------------------------------------------------------------------

SINCE = "Since March 2025, Nora Vance works at Halden as CTO."
JOINED = "Nora Vance joined Halden as CTO in March 2025."


def test_since_is_lower_bound_continuity_not_a_start():
    present = dataclasses.replace(NOW, start=at(SINCE, "works")[0], end=at(SINCE, "works")[1])
    o, c = employment(SINCE, [month(SINCE, "March 2025", "holds-since", 2025, 3), present])
    assert codes(o, c, schema=SCHEMA) == []
    vt, basis = valid_time(c)
    assert vt == ValidTime(None, d(2025, 4), SAID) and basis == "ongoing-at-observation"  # no start is stated


def test_since_encoded_as_a_start_is_rejected():
    o, c = employment(SINCE, [month(SINCE, "March 2025", "start", 2025, 3)])
    assert codes(o, c) == ["since-as-start"]


def test_joined_in_march_is_a_start():
    o, c = employment(JOINED, [month(JOINED, "March 2025", "start", 2025, 3)])
    assert codes(o, c) == [] and valid_time(c) == (ValidTime(d(2025, 3), d(2025, 4)), "unknown")


def test_the_distinction_changes_the_v2_answer_for_a_disputed_start():
    """The Phase 4 q01 pattern: January start, 'since March', May departure. Mid-March is no longer disputed."""
    jan = NS(id="jan", valid=ValidTime(d(2025, 1), d(2025, 2)), polarity="positive")
    left = NS(id="left", valid=ValidTime(to_earliest=d(2025, 5), to_latest=d(2025, 6)), polarity="positive")
    present = dataclasses.replace(NOW, start=at(SINCE, "works")[0], end=at(SINCE, "works")[1])
    _, since = employment(SINCE, [month(SINCE, "March 2025", "holds-since", 2025, 3), present])
    _, start = employment(SINCE, [month(SINCE, "March 2025", "start", 2025, 3), present])  # the old reading
    as_since = NS(id="since", valid=valid_time(since)[0], polarity="positive")
    as_start = NS(id="since", valid=ValidTime(d(2025, 3), d(2025, 4), to_earliest=SAID), polarity="positive")
    assert valid_time(start)[0] == as_start.valid
    assert classify([jan, as_start, left], d(2025, 3, 15), True).answer is Answer.UNKNOWN
    assert classify([jan, as_since, left], d(2025, 3, 15), True).answer is Answer.PRESUMED


# --- exact passages, participants and times -------------------------------------------------------------

def test_passages_participants_and_time_phrases_must_match_the_source_exactly():
    o, c = employment(JOINED, [month(JOINED, "March 2025", "start", 2025, 3)])
    moved = dataclasses.replace(c, passage=dataclasses.replace(c.passage, text="Nora joined Halden."))
    renamed = dataclasses.replace(c, participants=(dataclasses.replace(c.participants[0], surface="Nora"),
                                                   c.participants[1]))
    wrong_time = dataclasses.replace(c, times=(dataclasses.replace(c.times[0], phrase="April 2025"),))
    assert codes(o, moved) == ["passage"]
    assert codes(o, renamed) == ["participant"]
    assert codes(o, wrong_time) == ["time"]


def test_time_windows_are_checked():
    o, c = employment(JOINED, [month(JOINED, "March 2025", "start", 2025, 3)])
    inverted = dataclasses.replace(c, times=(dataclasses.replace(c.times[0], earliest=d(2025, 5)),))
    twice = dataclasses.replace(c, times=c.times * 2)
    left = "Nora Vance joined Halden as CTO in March 2025 and left in January 2025."
    o2, c2 = employment(left, [month(left, "March 2025", "start", 2025, 3), month(left, "January 2025", "end", 2025, 1)])
    assert codes(o, inverted) == ["time"]
    assert codes(o, twice) == ["time"]
    assert codes(o2, c2) == ["time"]


def test_a_coarse_holds_at_cannot_be_mapped_to_a_valid_time():
    text = "Nora Vance was CTO at Halden in March 2025."
    _, c = employment(text, [month(text, "March 2025", "holds-at", 2025, 3)])
    with pytest.raises(Unmappable):
        valid_time(c)


# --- attribution, modality, polarity, uncertainty, corrections -----------------------------------------

def test_attribution_modality_polarity_and_uncertainty_are_kept_and_checked():
    text = "Ravi wrote that Nora Vance will not join Halden after all."
    o, c = employment(text, (), polarity="negative", modality="planned", commitment="probable", confidence=0.6,
                      attribution=Attribution("Ravi", "reported", ("Ravi",), ("paraphrased",)))
    assert codes(o, c) == []
    assert codes(o, dataclasses.replace(c, modality="wished")) == ["modality"]
    assert codes(o, dataclasses.replace(c, attribution=Attribution(mode="overheard"))) == ["attribution"]
    assert codes(o, dataclasses.replace(c, attribution=Attribution(transmission=("photocopied",)))) == ["transmission"]
    assert codes(o, dataclasses.replace(c, confidence=1.5)) == ["confidence"]


def test_correction_relationships_name_a_candidate_or_an_existing_claim():
    text = "Correction: Nora Vance left Halden in May 2025."
    o, c = employment(text, [month(text, "May 2025", "end", 2025, 5)],
                      relations=(Relation("corrects", "claim:0123", "stated", "Correction:"),))
    assert codes(o, c) == []
    assert codes(o, dataclasses.replace(c, relations=(Relation("corrects", "elsewhere"),))) == ["relation"]
    assert codes(o, dataclasses.replace(c, relations=(Relation("overrides", "claim:0123"),))) == ["relation"]
    earlier = dataclasses.replace(c, relations=())
    later = dataclasses.replace(c, basis="inferred", relations=(Relation("corrects", earlier.id),))
    assert codes(o, earlier, later) == []
    # a candidate from an earlier observation's set is a legitimate target, though this set cannot check it
    assert codes(o, dataclasses.replace(c, relations=(Relation("corrects", "candidate:0123"),))) == []


# --- the set: version, observation, schema, serialisation, separation from memory ---------------------

def test_the_set_is_versioned_and_tied_to_one_observation():
    o, c = employment(JOINED)
    cs = one(o, c)
    assert [i.code for i in validate(dataclasses.replace(cs, ir_version="gupi.candidate/0"), o)] == ["version"]
    assert [i.code for i in validate(dataclasses.replace(cs, content_hash="x"), o)] == ["content-hash"]
    assert sorted(i.code for i in validate(cs, obs(JOINED + " "))) == ["content-hash", "observation", "passage"]


def test_schema_checks_types_roles_and_kinds_when_given():
    o, c = employment(JOINED)
    wrong_kind = dataclasses.replace(c, participants=(dataclasses.replace(c.participants[0], kind="organization"),
                                                      c.participants[1]))
    assert codes(o, wrong_kind, schema=SCHEMA) == ["schema"]
    assert codes(o, dataclasses.replace(c, claim_type="identity"), schema=SCHEMA) == ["schema"]
    assert codes(o, dataclasses.replace(c, values=(("salary", "high"),)), schema=SCHEMA) == ["schema"]


def test_round_trip_through_json_keeps_ids():
    present = dataclasses.replace(NOW, start=at(SINCE, "works")[0], end=at(SINCE, "works")[1])
    o, c = employment(SINCE, [month(SINCE, "March 2025", "holds-since", 2025, 3), present],
                      relations=(Relation("updates", "claim:0123", "inferred"),), confidence=0.8)
    cs = one(o, c)
    back = from_dict(to_dict(cs))
    assert back == cs and back.candidates[0].id == c.id and to_dict(cs)["candidates"][0]["id"] == c.id


def test_only_the_formation_pathway_touches_memory_or_typedb():
    """Candidates stay separate from memory: every module of the package except form.py (the explicit
    formation pathway, 6C) imports nothing that can write it."""
    src = Path(__file__).resolve().parents[2] / "src/gupi/formation"
    imported = set()
    for path in sorted(set(src.glob("*.py")) - {src / "form.py"}):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
            elif isinstance(node, ast.Import):
                imported |= {a.name for a in node.names}
    forbidden = {m for m in imported if m.startswith(("typedb", "gupi.memory", "gupi.typedb", "gupi.extraction",
                                                      "gupi.migrations", "gupi.retrieval"))}
    assert imported and not forbidden


def test_a_correction_cue_without_a_named_target_still_needs_review():
    """Found by the 6C development demonstration: the extractor names no target when the earlier statement
    was a different kind of boundary, but the passage still says it is a correction."""
    from gupi.formation.form import decide
    text = "Correction: Nora Vance left Halden in May 2025."
    _, c = employment(text, [month(text, "May 2025", "end", 2025, 5)])
    d = decide(c, [], {})
    assert (d.outcome, "could not be identified" in d.reason) == ("review", True)
    assert decide(c, [], {c.id: "reviewer-a"}).outcome == "formed"
    _, plain = employment(JOINED, [month(JOINED, "March 2025", "start", 2025, 3)])
    assert decide(plain, [], {}).outcome == "formed"
