"""The spreadsheet annotation template exports to JSON Lines without loss (docs/specialist/authoring-trial/dry-check)."""

import copy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DRY = ROOT / "docs/specialist/authoring-trial/dry-check"
spec = importlib.util.spec_from_file_location("annotation_export", ROOT / "scripts/annotation_export.py")
export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export)


def sheets():
    return export.read_sheets(DRY / "sheets")


def test_dry_check_sheets_are_valid_and_round_trip_losslessly():
    s = sheets()
    assert export.check(s, DRY) == []
    files = export.export(s, "dry")
    assert export.lost(s, files) == []
    assert all(s[name][1] for name in export.SHEETS)  # every sheet is exercised
    assert "shared.dry.jsonl" in files and "answers.dry.jsonl" in files


def test_template_headers_match_the_dry_check_sheets():
    template = export.read_sheets(ROOT / "docs/specialist/authoring-trial/annotation-template")
    assert {n: h for n, (h, _) in template.items()} == {n: h for n, (h, _) in sheets().items()}


def test_problems_are_reported_not_guessed():
    s = copy.deepcopy(sheets())
    s["statements"][1][0]["standing"] = "official"
    s["statements"][1][1]["transmission"] = "transcribed;rumoured"
    s["mentions"][1][0]["entity"] = "ent-nobody"
    s["mentions"][1][1]["start"] = "0"
    next(r for r in s["answer_evidence"][1] if r["kind"] == "essential")["set"] = "3"
    s["answer_sides"][1].pop()
    errors = "\n".join(export.check(s, DRY))
    assert "standing 'official' is not allowed" in errors
    assert "transmission rumoured is not allowed" in errors
    assert "entity ent-nobody is not an id in entities" in errors
    assert "text does not match the document" in errors
    assert "must be numbered 1, 2, ... without gaps" in errors
    assert "needs at least two sides" in errors
