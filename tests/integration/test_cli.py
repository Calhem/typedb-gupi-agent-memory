"""The review CLI end to end on the live server (offline rule extractor only)."""

import io
import json

import pytest
from helpers import Clock

from gupi.cli import main

pytestmark = pytest.mark.integration

CONVERSATION = {"id": "cli-1", "source": "team-chat", "messages": [
    {"key": "m1", "at": "2025-02-01T10:00:00Z", "text": "Marco Rossi has reported to Elena Petrova since 2023."},
    {"key": "m2", "at": "2025-09-15T16:00:00Z", "text": "Correction: Marco Rossi stopped reporting to Elena Petrova in April 2025."},
    {"key": "m3", "at": "2025-09-16T09:00:00Z", "text": "Marco Rossi reports to Dana Li."},
]}


@pytest.fixture
def gupi(driver, database, tmp_path):
    clock = Clock("2025-09-20")
    path = tmp_path / "conversation.json"
    path.write_text(json.dumps(CONVERSATION))

    def run(*argv, ok=True):
        out = io.StringIO()
        code = main(["--database", database, *[str(a) for a in argv]], out=out, driver=driver, clock=clock)
        assert (code == 0) == ok, out.getvalue()
        return out.getvalue()
    run.clock, run.path = clock, path
    return run


def ids_in(queue_output):
    return [line.split()[0] for line in queue_output.splitlines() if line and not line.startswith(" ")]


def id_for(queue_output, quote):
    lines = queue_output.splitlines()
    return next(lines[i - 1].split()[0] for i, line in enumerate(lines) if quote in line)


def test_review_workflow(gupi):
    assert "3 claim(s) extracted as hypotheses" in gupi("ingest", gupi.path, "--create")
    assert "0 claim(s) extracted" in gupi("ingest", gupi.path)  # idempotent
    queue = gupi("queue")
    first = id_for(queue, "since 2023")
    correction = id_for(queue, "Correction:")
    dana = id_for(queue, "Dana Li.")
    assert "reporting(manager=Elena Petrova, report=Marco Rossi)" in queue and "[explicit]" in queue

    gupi("accept", first, correction, "--by", "reviewer-a", "--reason", "matches HR records")
    gupi.clock.set("2025-09-21")
    queue = gupi("queue")
    assert ids_in(queue) == [dana]
    assert "! contradiction" not in queue  # Elena ended in April; Dana from September: sequential

    shown = gupi("show", first)
    assert "status now: accepted" in shown and "accepted by reviewer-a: matches HR records" in shown
    assert "“Marco Rossi has reported to Elena Petrova since 2023.”" in shown

    corrections = gupi("corrections")
    assert f"supersede {first} with {correction}" in corrections
    out = gupi("supersede", first, correction, "--by", "reviewer-a")
    supersession = out.strip().split("(")[-1].rstrip(")")
    gupi.clock.set("2025-09-22")
    assert "withdrawn" in gupi("unsupersede", supersession, "--by", "reviewer-a", "--reason", "mistake")
    assert "withdrawn" in gupi("show", first) and "status now: accepted" in gupi("show", first)


def test_possibly_sequential_values_are_not_suggested_as_corrections(gupi, tmp_path):
    promotion = {"id": "cli-2", "source": "hr", "messages": [
        {"key": "p1", "at": "2025-02-01T10:00:00Z", "text": "Marco Rossi works at Brightline as a Senior Engineer."},
        {"key": "p2", "at": "2025-09-20T09:00:00Z", "text": "Marco Rossi is a Staff Engineer at Brightline."}]}
    path = tmp_path / "promotion.json"
    path.write_text(json.dumps(promotion))
    gupi("ingest", path, "--create")
    gupi("accept", *ids_in(gupi("queue")), "--by", "reviewer-a")
    assert "differing-evidence" in gupi("conflicts") and "possibly sequential" in gupi("conflicts")
    assert "No suggested corrections." in gupi("corrections")


def test_errors_are_reported_not_raised(gupi):
    gupi("ingest", gupi.path, "--create")
    gupi("show", "nope", ok=False)
    gupi("accept", "nope", "--by", "x", ok=False)
    with pytest.raises(SystemExit):  # argparse: --by is required
        gupi("accept", "abc")
