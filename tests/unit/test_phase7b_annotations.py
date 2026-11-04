"""The Phase 7B annotation checker: structure only, never content (fixtures are developer-authored DEV examples)."""

import csv
import shutil
from pathlib import Path

from gupi.benchmarks.phase7b import annotations as ann

DEV = Path(__file__).resolve().parents[1] / "fixtures" / "phase7b-dev"


def copy(tmp_path, change=None):
    for f in DEV.glob("*.csv"):
        shutil.copy(f, tmp_path / f.name)
    if change:
        path = tmp_path / "assertions-A.csv"
        cols, rows = ann.read(path)
        rows[0].update(change)
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
    return tmp_path


def test_dev_examples_and_blank_templates_are_structurally_valid():
    assert ann.check(DEV) == []
    assert ann.check(Path(__file__).resolve().parents[2] / "docs" / "evaluation" / "phase-7b" / "annotation-templates") == []


def test_spans_participants_and_claimants_must_occur_in_the_passage(tmp_path):
    problems = ann.check(copy(tmp_path, {"span_text": "Pellwick appointed Mara Quist", "participants": "employee=M. Quist | employer=Pellwick",
                                         "original_claimant": "Dana"}))
    assert any("span_text does not occur" in p for p in problems)
    assert any("'M. Quist' does not occur" in p for p in problems)
    assert not any("original_claimant" in p for p in problems)   # "Dana" does occur (inside "Dana Okoro")


def test_values_ids_and_targets_are_checked(tmp_path):
    problems = ann.check(copy(tmp_path, {"commitment": "definitely", "relation_to_earlier": "corrects",
                                         "target_assertion_id": "DEV-999", "representable": "partial",
                                         "representation_gap": ""}))
    assert any("commitment 'definitely'" in p for p in problems)
    assert any("'DEV-999' is not an assertion_id" in p for p in problems)
    assert any("needs a representation_gap" in p for p in problems)


def test_repeated_spans_need_an_occurrence():
    text = "Ivo left. Ivo left."
    assert ann.span_location(text, "Ivo left", "2") == (10, 18)
    assert ann.span_location(text, "Ivo left", "3") is None


def test_compare_lists_field_disagreements_for_adjudication():
    rows = ann.compare(DEV / "assertions-A.csv", DEV / "assertions-B.csv", DEV / "passages.csv")
    assert {(r["field"], r["annotator_a"], r["annotator_b"]) for r in rows} == {
        ("commitment", "probable", "certain"), ("expected_admission", "review", "formed")}
