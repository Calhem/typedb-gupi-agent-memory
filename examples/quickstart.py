"""Record two sources about Alice, accept one, correct it later, and ask questions at different times.

Run with TypeDB up (`docker compose up -d`): uv run python -I examples/quickstart.py
Uses a throwaway database `gupi-example` and deletes it afterwards.
"""

from datetime import datetime, timezone

from gupi.memory import Memory
from gupi.records import Batch, Claim, Evidence, Observation, Referent, Source
from gupi.temporal import ValidTime


def utc(*parts):
    return datetime(*parts, tzinfo=timezone.utc)


class Clock:  # GUPI stamps transaction time from a clock; a fixed one makes the example repeatable
    now = utc(2025, 1, 10)

    def __call__(self):
        return self.now


clock = Clock()
memory = Memory.open("gupi-example", packs=("core", "people"), create=True, clock=clock)
try:
    hr = Source("src:hr", "text", label="HR notes")
    note = Observation("src:hr", "note-1", "Alice has reported to Bob since March 2024.", observed_at=utc(2025, 1, 10))
    people = (Referent("p:alice", "person", "Alice"), Referent("p:bob", "person", "Bob"))
    roles = {"report": "p:alice", "manager": "p:bob"}
    first = Claim("reporting", roles, (Evidence(note.id, 0, len(note.content)),),
                  ValidTime(utc(2024, 3, 1), utc(2024, 4, 1), to_earliest=note.observed_at),
                  valid_to_basis="ongoing-at-observation")
    memory.ingest(Batch((hr,), (note,), people, (first,)))
    memory.review(first.id, "accepted", "example")

    clock.now = utc(2025, 11, 15)
    fix = Observation("src:hr", "note-2", "Alice stopped reporting to Bob in June.", observed_at=utc(2025, 11, 14))
    second = Claim("reporting", roles, (Evidence(fix.id, 0, len(fix.content)),),
                   ValidTime(utc(2024, 3, 1), utc(2024, 4, 1), utc(2025, 6, 1), utc(2025, 7, 1)),
                   valid_to_basis="stated")
    memory.ingest(Batch((hr,), (fix,), people, (second,)))
    memory.review(second.id, "accepted", "example")
    memory.supersede(first.id, second.id, reason="late correction")

    for label, believed_at in (("as believed in March 2025", utc(2025, 3, 15)), ("as believed now", clock.now)):
        result = memory.ask("reporting", roles, utc(2025, 8, 1), believed_at=believed_at)
        sources = [e.quote for c, _ in result.believed for e in c.evidence]
        print(f"Did Alice report to Bob in August 2025, {label}? {result.answer.value}  (evidence: {sources})")
finally:
    memory.driver.databases.get("gupi-example").delete()
