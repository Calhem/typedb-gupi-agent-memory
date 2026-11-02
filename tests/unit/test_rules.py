from datetime import datetime, timezone

from gupi.extraction.contract import SchemaInfo
from gupi.extraction.pipeline import ExtractionRequest
from gupi.extraction.rules import RuleExtractor

WHEN = datetime(2025, 6, 10, tzinfo=timezone.utc)
SCHEMA = SchemaInfo(frozenset(), {}, {})


def run(text):
    return RuleExtractor().extract(ExtractionRequest(text, WHEN, SCHEMA))


def test_spans_quotes_and_time_phrases_come_from_the_text():
    text = "Correction: Marco Rossi stopped reporting to Elena Petrova in April 2025."
    out = run(text)
    (claim,) = out["claims"]
    assert [text[m["start"]:m["end"]] for m in out["mentions"]] == ["Marco Rossi", "Elena Petrova"]
    assert text[claim["start"]:claim["end"]] == claim["quote"] == text
    assert claim["time"] == {"start": None, "end": "April 2025", "ongoing": False}
    assert claim["basis"] == "explicit"


def test_leading_time_clause_and_titles():
    out = run("Since June 2025, Priya Shah reports to Dana Li. Marco Rossi is a Staff Engineer at Brightline.")
    first, second = out["claims"]
    assert first["type"] == "reporting" and first["time"]["start"] == "June 2025" and first["time"]["ongoing"]
    assert second["type"] == "employment" and second["values"] == {"job-title": "Staff Engineer"}


def test_generic_statement_and_unrecognised_text():
    (claim,) = run("Alice is learning Rust.")["claims"]
    assert (claim["type"], claim["predicate"], claim["object_text"]) == ("statement", "is learning", "Rust")
    assert run("He used to work at Initech.") == {"mentions": [], "claims": []}  # pronouns: not handled
    assert run("Nothing to see here") == {"mentions": [], "claims": []}


def test_deterministic():
    text = "Priya Shah joined Northwind as Head of Data in January 2025."
    assert run(text) == run(text)
