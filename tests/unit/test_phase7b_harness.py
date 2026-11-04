"""The Phase 7B offline harness: scoring rules on purpose-built cases, offline operation, determinism.
All inputs are developer-authored test material."""

import csv
import json
import socket

import pytest

from gupi.benchmarks.phase7b import annotations as ann, harness
from gupi.formation.model_candidate import RESPONSE_FORMAT

FIX = harness.Path(__file__).resolve().parents[1] / "fixtures" / "phase7b-dev" / "offline"
COLS = ann.ASSERTION_COLUMNS


def corpus(tmp_path, passages, gold, responses):
    with open(tmp_path / "passages.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(ann.PASSAGE_COLUMNS)
        for pid, text in passages:
            w.writerow([pid, "DEV", "", "", "dev", "note", "Ivo Marsh", "2025-08-20", text])
    with open(tmp_path / "assertions.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for g in gold:
            row = dict.fromkeys(COLS, "")
            row.update(source_speaker="Ivo Marsh", attribution_mode="direct", independent_origin="yes", polarity="positive",
                       modality="actual", commitment="certain", allegation="no", time_kind="none", time_basis="none",
                       relation_to_earlier="none", literal_or_inferred="literal", representable="yes", expected_admission="formed")
            row.update(g)
            w.writerow(row)
    (tmp_path / "responses.json").write_text(json.dumps({"responses": responses}))
    return tmp_path


def resp(*assertions, outcome="assertions"):
    return {"format": RESPONSE_FORMAT, "outcome": outcome, "assertions": list(assertions), "problems": []}


def emp(ev, who, org, **kw):
    a = {"evidence": ev, "relation": "employment",
         "participants": [{"role": "employee", "text": who, "kind": "person", "is_pronoun_or_vague": False},
                          {"role": "employer", "text": org, "kind": "organization", "is_pronoun_or_vague": False}],
         "times": [], "polarity": "positive", "modality": "actual", "commitment": "certain",
         "attribution": {"mode": "direct", "claimant": None, "claimant_kind": None, "via": []}, "basis": "explicit"}
    a.update(kw)
    return a


def gold(pid, n, span, who, org, **kw):
    return {"assertion_id": f"{pid}-a{n}", "passage_id": pid, "span_text": span, "relation": "employment",
            "gupi_claim_type": "employment", "participants": f"employee={who} | employer={org}", **kw}


def model(result):
    return result["systems"][harness.MODEL_METHOD]


def test_matching_tiers_duplicates_unsupported_and_severe_errors(tmp_path):
    texts = [("X-1", "Nora Vance works at Halden."),
             ("X-2", "Nora Vance works at Halden, says Ivo. Not confirmed yet."),
             ("X-3", "Mara Quist works at Pellwick and Halden."),
             ("X-4", "Can we meet on Friday?")]
    g = [gold("X-1", 1, "Nora Vance works at Halden", "Nora Vance", "Halden"),
         gold("X-2", 1, "Nora Vance works at Halden", "Nora Vance", "Halden", commitment="probable", expected_admission="review"),
         gold("X-3", 1, "Mara Quist works at Pellwick", "Mara Quist", "Pellwick")]
    r = {"X-1": resp(emp("Nora Vance works at Halden", "Nora Vance", "Halden"),
                     emp("Nora Vance works at Halden", "Nora Vance", "Halden", times=[{"text": "works", "kind": "holds-at"}])),
         "X-2": resp(emp("Nora Vance works at Halden", "Nora Vance", "Halden")),            # certain, gold probable
         "X-3": resp(emp("Mara Quist works at Pellwick and Halden", "Mara Quist", "Halden")),  # wrong employer
         "X-4": resp(emp("Can we meet on Friday", "Friday", "Friday"))}                       # invented
    out = model(harness.run(corpus(tmp_path, texts, g, r), responses=tmp_path / "responses.json"))
    s = out["summary"]
    assert (s["counts"]["matched"], s["counts"]["duplicates"], s["counts"]["partial"], s["counts"]["unsupported"]) == (2, 1, 1, 1)
    assert (s["precision"]["k"], s["precision"]["n"], s["recall"]["k"], s["recall"]["n"]) == (2, 4, 2, 3)
    errors = sorted((e["passage"], e["error"]) for e in out["severe"])
    assert errors == [("X-2", "unsupported certainty"), ("X-3", "invented entity"), ("X-4", "invented assertion")]
    assert [a["why"].split(":")[0] for a in out["adjudicate"]] == ["partial match"]   # for a person, not an LLM


def test_abstentions_on_ambiguous_gold_are_counted_as_appropriate(tmp_path):
    texts = [("Y-1", "Dana Okoro told me Mara Quist reports to her now.")]
    g = [{"assertion_id": "Y-1-a1", "passage_id": "Y-1", "span_text": "Mara Quist reports to her now", "relation": "reporting",
          "gupi_claim_type": "reporting", "participants": "report=Mara Quist | manager=her", "resolution": "her=Dana Okoro",
          "literal_or_inferred": "inferred", "ambiguity": "who 'her' is"}]
    a = emp("Mara Quist reports to her now", "Mara Quist", "her")
    a.update(relation="reporting", participants=[{"role": "report", "text": "Mara Quist", "kind": "person", "is_pronoun_or_vague": False},
                                                 {"role": "manager", "text": "her", "kind": "person", "is_pronoun_or_vague": True}])
    out = model(harness.run(corpus(tmp_path, texts, g, {"Y-1": resp(a)}), responses=tmp_path / "responses.json"))
    assert out["summary"]["counts"]["abstained"] == out["summary"]["counts"]["abstained_appropriately"] == 1
    assert out["summary"]["recall"]["k"] == 0


def test_the_harness_runs_without_network_access(monkeypatch):
    def refuse(*args, **kwargs):
        raise OSError("network access attempted during an offline run")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    a = harness.run(FIX, responses=FIX / "responses.json")
    b = harness.run(FIX, responses=FIX / "responses.json")
    assert a == b and set(a["systems"]) == {"rules:v2.1", harness.MODEL_METHOD}
    assert "anthropic" not in " ".join(sorted(__import__("sys").modules))


def test_the_corpus_must_pass_the_structural_check(tmp_path):
    corpus(tmp_path, [("Z-1", "Nora Vance works at Halden.")],
           [gold("Z-1", 1, "Nora works at Halden", "Nora Vance", "Halden")], {})
    with pytest.raises(ValueError, match="structural check"):
        harness.run(tmp_path)


def test_wilson_intervals():
    assert harness.wilson(0, 0)["rate"] is None
    w = harness.wilson(17, 20)
    assert w["rate"] == 0.85 and 0.63 < w["low"] < 0.65 and 0.94 < w["high"] < 0.96
