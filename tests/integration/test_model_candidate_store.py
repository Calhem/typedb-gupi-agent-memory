"""model:candidate-v1 candidates go through the same validation and formation as rules candidates
(developer-authored responses; offline)."""

import sys
from datetime import timedelta
from pathlib import Path

import pytest

from gupi.formation import store
from gupi.formation.form import live_schema
from gupi.formation.model_candidate import ModelCandidateV1
from gupi.records import Batch, Context, Observation, Referent, Source

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "unit"))
from test_model_candidate import NORA, assertion, response  # noqa: E402

pytestmark = pytest.mark.integration


def submit(memory, clock, text, resp, key):
    clock.now = clock.now + timedelta(minutes=5)
    obs = Observation("src:m", key, text, clock.now, "ctx:m", "p:ivo")
    memory.ingest(Batch((Source("src:m", "mail"),), (obs,), (Referent("p:ivo", "person", "Ivo Marsh"),),
                        contexts=(Context("ctx:m", "conversation"),)))
    cset, report = ModelCandidateV1().extract(obs, schema=live_schema(memory), response=resp)
    clock.now += timedelta(minutes=1)
    result = store.submit(memory, obs, cset) if cset.candidates else None
    return [store.get(memory, c.id) for c in cset.candidates], report, result


def test_formation_safeguards_apply_unchanged(memory, clock):
    plain, _, _ = submit(memory, clock, "Nora Vance joined Halden in March 2025.",
                         response(assertion("Nora Vance joined Halden in March 2025", NORA, times=[("March 2025", "start")])), "m1")
    hedged, _, _ = submit(memory, clock, "Probably Nora Vance works at Halden.",
                          response(assertion("Probably Nora Vance works at Halden", NORA)), "m2")
    planned, _, _ = submit(memory, clock, "Nora Vance will join Pellwick in May 2026.",
                           response(assertion("Nora Vance will join Pellwick in May 2026",
                                              [("employee", "Nora Vance", "person"), ("employer", "Pellwick", "organization")],
                                              times=[("May 2026", "start")], modality="planned")), "m3")
    owns, _, _ = submit(memory, clock, "Halden Holdings owns Pellwick.",
                        response(assertion("Halden Holdings owns Pellwick", [("subject", "Halden Holdings", "organization"),
                                                                              ("object", "Pellwick", "organization")],
                                           relation="statement", predicate="owns")), "m4")
    assert [s.status for s in plain + hedged + planned + owns] == ["formed", "review", "withheld", "formed"]
    assert hedged[0].candidate.commitment == "unknown"


def test_schema_rules_reject_what_the_model_gets_wrong(memory, clock):
    wrong_kind = response(assertion("Nora Vance works at Ivo Marsh", [("employee", "Nora Vance", "person"),
                                                                     ("employer", "Ivo Marsh", "person")]))
    stored, report, _ = submit(memory, clock, "Nora Vance works at Ivo Marsh.", wrong_kind, "m5")
    assert stored == [] and [o["kind"] for o in report.outcomes] == ["validation"]
    assert not memory.all_claims()
