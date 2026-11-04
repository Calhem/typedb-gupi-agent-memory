"""gupi.candidate/1.1 (docs/evaluation/phase-7b/stage-2b/candidate-format-1.1.md): additive and backward-compatible."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from gupi import ids
from gupi.formation.candidate import (
    IR_VERSION, IR_VERSION_1_1, Attribution, Candidate, CandidateSet, Participant, Passage, Relation, from_dict, to_dict,
)
from gupi.formation.rules_v2 import RulesV2
from gupi.formation.validate import validate
from gupi.records import Observation

ROOT = Path(__file__).resolve().parents[2]
SAID = datetime(2025, 8, 20, 9, tzinfo=timezone.utc)
TEXT = "According to Halden Press, Nora Vance joined Halden in March 2025."


def obs(text=TEXT):
    return Observation("src:t", "k", text, SAID, "ctx:t", "p:a")


def cand(o, kind="organisation", asserted_by="Halden Press", relations=()):
    s = o.content.index("Nora Vance")
    return Candidate("employment", Passage(o.id, 0, len(o.content), o.content),
                     (Participant("employee", "Nora Vance", s, s + 10, "person"),
                      Participant("employer", "Halden", o.content.index("Halden in"), o.content.index("Halden in") + 6, "organization")),
                     attribution=Attribution(asserted_by, "reported", asserted_by_kind=kind), relations=relations)


def cset(o, *cs, version=IR_VERSION_1_1):
    return CandidateSet(o.id, ids.content_hash(o.content), "test", tuple(cs), version)


def codes(cs, o):
    return sorted({i.code for i in validate(cs, o)})


def test_format_1_0_candidate_ids_are_unchanged():
    """The ids the Phase 6D first run recorded for its rules:v2 candidates are reproduced exactly."""
    run = json.loads((ROOT / "docs/evaluation/phase-6d/first-run/world.json").read_text())
    world = json.loads((ROOT / "tests/fixtures/retrieval/world.json").read_text())
    prior, checked = {}, 0
    for conv in world["conversations"]:
        for m in sorted(conv["messages"], key=lambda m: m["at"]):
            said = datetime.fromisoformat(m["at"].replace("Z", "+00:00"))
            o = Observation(f"src:{conv['source']}", m["key"], m["text"], said, f"conv:{conv['id']}")
            got, _ = RulesV2().extract(o, prior=tuple(prior.setdefault(conv["id"], [])))
            prior[conv["id"]].append(got)
            assert got.ir_version == IR_VERSION
            assert [c.id for c in got.candidates] == [c["id"] for c in run["trace"][m["key"]]["candidates"]]
            checked += len(got.candidates)
    assert checked == 11


def test_a_1_1_candidate_round_trips():
    o = obs()
    c = cand(o, relations=(Relation("corrects", None, "stated", "Correction"),))
    back = from_dict(json.loads(json.dumps(to_dict(cset(o, c)))))
    assert back.ir_version == IR_VERSION_1_1 and back.candidates[0] == c and back.candidates[0].id == c.id
    assert back.candidates[0].attribution.asserted_by_kind == "organisation"


def test_absent_kind_is_absent_not_person():
    o = obs()
    c = cand(o, kind=None)
    assert c.attribution.asserted_by_kind is None
    assert "asserted_by_kind" not in to_dict(cset(o, c, version=IR_VERSION))["candidates"][0]["attribution"]


def test_valid_1_1_candidates_pass():
    o = obs()
    assert codes(cset(o, cand(o)), o) == []
    assert codes(cset(o, cand(o, kind="unknown")), o) == []
    assert codes(cset(o, cand(o, relations=(Relation("retracts", None, "stated", None),))), o) == []


@pytest.mark.parametrize("make, code", [
    (lambda o: cset(o, cand(o), version=IR_VERSION), "version"),                              # 1.1 field in a 1.0 set
    (lambda o: cset(o, cand(o, relations=(Relation("corrects", None),)), version=IR_VERSION), "version"),
    (lambda o: cset(o, cand(o, kind="company")), "attribution"),
    (lambda o: cset(o, cand(o, asserted_by=None, kind="person")), "attribution"),            # a kind with no claimant
    (lambda o: cset(o, cand(o, asserted_by="Reuters")), "attribution"),                      # not in the text
    (lambda o: cset(o, cand(o, relations=(Relation("repeats", None),))), "relation"),       # only corrections may be null
    (lambda o: cset(o, cand(o, relations=(Relation("contradicts", None),))), "relation"),
    (lambda o: CandidateSet(o.id, ids.content_hash(o.content), "test", (cand(o),), "gupi.candidate/2"), "version"),
])
def test_invalid_1_1_candidates_are_rejected(make, code):
    o = obs()
    assert code in codes(make(o), o)


def test_a_stored_1_0_payload_stays_readable():
    o = obs("Nora Vance joined Halden in March 2025.")
    old, _ = RulesV2().extract(o)
    payload = json.dumps(to_dict(old), sort_keys=True)
    back = from_dict(json.loads(payload))
    assert back == old and back.ir_version == IR_VERSION and validate(back, o) == []
