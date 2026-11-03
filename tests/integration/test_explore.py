"""Multi-hop exploration, chained questions and history, on the live server (separate from the benchmark)."""

import pytest
from helpers import CHAT, HR, observe, record, reports, utc

from gupi import retrieval
from gupi.records import Referent
from gupi.temporal import Answer, ValidTime

pytestmark = pytest.mark.integration

PEOPLE_EXTRA = (Referent("p:carol", "person", "Carol"), Referent("p:dan", "person", "Dan"))


@pytest.fixture(autouse=True)
def no_full_scans(monkeypatch):
    monkeypatch.setattr(retrieval, "all_claims", lambda *a, **k: (_ for _ in ()).throw(AssertionError("full scan")))


@pytest.fixture
def chain(memory, clock):
    """Alice -> Bob -> Carol -> Dan reporting lines, all since January 2025, said in March."""
    from gupi.records import Batch
    clock.set("2025-03-02")
    memory.ingest(Batch(referents=PEOPLE_EXTRA))
    pairs = [("p:alice", "p:bob"), ("p:bob", "p:carol"), ("p:carol", "p:dan")]
    obs, claims = [], []
    for i, (report, manager) in enumerate(pairs):
        o = observe(HR, f"hr-{i}", f"{report} reports to {manager} since January.", "2025-03-01")
        obs.append(o)
        from helpers import claim
        claims.append(claim("reporting", {"report": report, "manager": manager}, o,
                            ValidTime(utc("2025-01-01"), utc("2025-01-01"), to_earliest=utc("2025-03-01"))))
    record(memory, obs, claims)
    memory.review_many([(c.id, "accepted") for c in claims], "reviewer")
    return claims


def test_explore_walks_hop_by_hop_with_limits(memory, chain):
    g = memory.explore("p:alice", depth=2, valid_at=utc("2025-02-01"))
    assert {n: i["hop"] for n, i in g.nodes.items()} == {"p:alice": 0, "p:bob": 1, "p:carol": 2}
    assert all(e["truth"] == "true" for e in g.edges) and len(g.steps) == 2
    deep = memory.explore("p:alice", depth=5)
    assert set(deep.nodes) == {"p:alice", "p:bob", "p:carol", "p:dan"} and not deep.truncated
    capped = memory.explore("p:alice", depth=5, max_nodes=2)
    assert len(capped.nodes) == 2 and capped.truncated


def test_follow_answers_each_hop_and_stops_where_knowledge_stops(memory, chain):
    up = ("reporting", "report", "manager")
    (path,) = memory.follow("p:alice", [up, up], utc("2025-02-01"))
    assert [h.result.binding for h in path] == [["Bob"], ["Carol"]]
    assert all(h.result.citations for h in path)
    (early,) = memory.follow("p:alice", [up, up], utc("2024-06-01"))  # before any line existed
    assert len(early) == 1 and early[0].result.answer is Answer.FALSE


def test_history_shows_both_time_axes(memory, clock, chain):
    clock.set("2025-04-01")
    memory.review(chain[0].id, "rejected", "reviewer", reason="wrong team")
    h = memory.history("p:alice")
    assert [e.event for e in h] == ["recorded", "accepted", "rejected"]
    assert h[0].period == "2025-01-01 to at least 2025-03-01"
    assert h[-1].at == utc("2025-04-01") and "wrong team" in h[-1].description
