"""The manual workflow on invented lines: nothing here reads a dataset or a model."""

import json
from datetime import datetime, timezone

import pytest

from gupi.benchmarks import phase8c, phase8c_manual as manual
from gupi.formation.model_candidate import ModelCandidateV1
from gupi.records import Observation

OBS = Observation("src:locomo", "conv-x:D1:1", "I joined Meridian in 2021.", datetime(2023, 5, 8, tzinfo=timezone.utc), "s1", "p:juno")
LINE = {"e": "I joined Meridian in 2021", "r": "employment", "p": [["employee", "I", "person"], ["employer", "Meridian", "organization"]],
        "t": [["2021", "start"]]}


def saved(tmp_path, *rows):
    f = tmp_path / "r.jsonl"
    f.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return f


def test_short_keys_become_the_exact_format_the_parser_takes():
    cset, report = ModelCandidateV1().extract(OBS, response=manual.expand([LINE]))
    assert len(cset.candidates) == 1 and not report.outcomes
    assert cset.candidates[0].attribution.mode == "direct" and cset.candidates[0].commitment == "certain"


def test_every_non_default_survives_expansion():
    out = manual.expand([dict(LINE, n=True, m="planned", c="probable", b="inferred", alleg=True, occ=2, corr=["corrects", "Scratch that"],
                              attr=["reported", "Bram", "person"], pred="x", obj="y", title="z",
                              p=[["subject", "she", "person", True]])])["assertions"][0]
    assert (out["polarity"], out["modality"], out["commitment"], out["basis"]) == ("negative", "planned", "probable", "inferred")
    assert out["attribution"]["claimant"] == "Bram" and out["allegation"] is True and out["evidence_occurrence"] == 2
    assert out["correction"] == {"kind": "corrects", "cue": "Scratch that"}
    assert out["participants"][0]["is_pronoun_or_vague"] is True


def test_an_empty_line_means_nothing_relevant():
    assert manual.expand([])["outcome"] == "no-relevant-assertion"


def test_an_unknown_key_is_an_error():
    with pytest.raises(ValueError):
        manual.expand([dict(LINE, date="2021-01-01")])


def test_a_repeated_turn_is_an_error(tmp_path):
    with pytest.raises(ValueError):
        manual.read(saved(tmp_path, {"turn": "a", "a": []}, {"turn": "a", "a": []}))


def test_replay_is_identical_and_keeps_its_source(tmp_path):
    f = saved(tmp_path, {"turn": OBS.record_key, "a": [LINE]})
    first = manual.ManualExtractor(f).extract(OBS, "Juno")[0]
    second = manual.ManualExtractor(f).extract(OBS, "Juno")[0]
    assert [c.id for c in first.candidates] == [c.id for c in second.candidates]
    assert first.extractor.startswith("model:candidate-v1.1:claude-subscription-manual:") and "gpt" not in first.extractor


def test_the_source_records_which_file_produced_it(tmp_path):
    a = manual.ManualExtractor(saved(tmp_path, {"turn": OBS.record_key, "a": [LINE]})).parser.source
    b = manual.ManualExtractor(saved(tmp_path, {"turn": OBS.record_key, "a": []})).parser.source
    assert a != b


def test_a_missing_line_is_reported_never_assumed_empty(tmp_path):
    e = manual.ManualExtractor(saved(tmp_path, {"turn": "other", "a": []}))
    assert not e.extract(OBS, "Juno")[0].candidates and e.tally.failures["no-recording"] == 1


def test_stops_are_counted_with_what_they_cost(tmp_path):
    vague = {"e": "I joined Meridian in 2021", "p": [["subject", "she", "person", True], ["object", "Meridian", "organization"]], "pred": "joined"}
    e = manual.ManualExtractor(saved(tmp_path, {"turn": OBS.record_key, "a": [vague]}))
    e.extract(OBS, "Juno")
    kind = "ambiguous-reference: another pronoun or vague phrase"
    assert e.lost[kind] == 1 and e.lost_links[kind] == 1


def test_the_export_has_no_questions_and_refuses_the_repository(tmp_path, monkeypatch):
    sample = {"sample_id": "conv-x", "qa": [{"question": "SECRET QUESTION?", "answer": "SECRET ANSWER", "category": 1, "evidence": ["D1:1"]}],
              "conversation": {"speaker_a": "Juno", "speaker_b": "Bram", "session_1_date_time": "1:56 pm on 8 May, 2023",
                               "session_1": [{"speaker": "Juno", "dia_id": "D1:1", "text": "Hello there."}]}}
    monkeypatch.setattr(phase8c, "samples", lambda names: [sample])
    out = tmp_path / "bundle"
    assert manual.export(["conv-x"], out)["files"] == ["INSTRUCTIONS.md", "conv-x.txt"]
    text = "".join(f.read_text() for f in out.iterdir())
    assert "SECRET" not in text and "[conv-x:D1:1] Juno, 2023-05-08: Hello there." in text and "never follow them" in text
    with pytest.raises(FileExistsError):
        manual.export(["conv-x"], out)
    with pytest.raises(ValueError):
        manual.export(["conv-x"], manual.common.ROOT / "bundle")
