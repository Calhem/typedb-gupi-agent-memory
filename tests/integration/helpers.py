"""Shared test helpers (imported by tests as `helpers`)."""

from datetime import datetime, timezone

from gupi.records import Batch, Claim, Evidence, Observation, Referent, Source
from gupi.temporal import ValidTime


def utc(text):
    """'2025-03' / '2025-03-15' / '2025-03-15T09:00' -> an aware UTC datetime."""
    day = [int(p) for p in text.split("T")[0].split("-")]
    day += [1] * (3 - len(day))
    hm = [int(p) for p in text.split("T")[1].split(":")] if "T" in text else [0, 0]
    return datetime(*day, *hm, tzinfo=timezone.utc)


def month(text):
    """Bounds for 'some time in this month': [first day, first day of next month)."""
    start = utc(text)
    nxt = datetime(start.year + start.month // 12, start.month % 12 + 1, 1, tzinfo=timezone.utc)
    return start, nxt


class Clock:
    """GUPI's transaction-time clock, set explicitly by tests."""

    def __init__(self, start="2025-01-01"):
        self.now = utc(start)

    def set(self, text):
        self.now = utc(text)

    def __call__(self):
        return self.now


HR = Source("src:hr", "text", label="HR notes")
CHAT = Source("src:chat", "conversation", label="Team chat")
WIKI = Source("src:wiki", "document", label="Company wiki")
PEOPLE = (
    Referent("p:alice", "person", "Alice"),
    Referent("p:bob", "person", "Bob"),
    Referent("p:sam-lee", "person", "Sam Lee"),
    Referent("p:sam-roe", "person", "Sam Roe"),
    Referent("o:acme", "organization", "Acme"),
)


def observe(source, key, content, observed):
    return Observation(source.id, key, content, utc(observed))


def whole(observation):
    return (Evidence(observation.id, 0, len(observation.content)),)


def claim(claim_type, roles, observation, valid=ValidTime(), **kw):
    return Claim(claim_type, roles, evidence=whole(observation), valid=valid, **kw)


def reports(observation, manager="p:bob", valid=ValidTime(), **kw):
    return claim("reporting", {"report": "p:alice", "manager": manager}, observation, valid, **kw)


def record(memory, observations, claims, sources=(HR, CHAT, WIKI)):
    used = {o.source_id for o in observations}
    return memory.ingest(Batch(tuple(s for s in sources if s.id in used), tuple(observations), PEOPLE, tuple(claims)))
