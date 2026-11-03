"""Development-only demonstration (Phase 6C): the Phase 2 development conversations, ingested, extracted by
rules:v2, formed, then queried under answer semantics v2.

Not a benchmark: the development split shaped rules:v1, on which rules:v2 builds. The point is that formed
claims can be queried, and that what waits for review does not change memory."""

import json
from datetime import datetime
from pathlib import Path

import pytest
from helpers import utc

from gupi.extraction.contract import referent_id
from gupi.formation.form import form
from gupi.formation.rules_v2 import RulesV2
from gupi.records import Batch, Context, Observation, Source
from gupi.temporal import Answer

pytestmark = pytest.mark.integration
DEV = Path(__file__).resolve().parents[1] / "fixtures" / "conversations" / "dev"


@pytest.fixture
def formed(memory, clock):
    totals = {"formed": 0, "withheld": 0, "review": 0, "rejected": 0}
    for path in sorted(DEV.glob("*.json")):
        conv = json.loads(path.read_text())
        source, ctx = Source("src:" + conv["id"], "conversation"), Context("ctx:" + conv["id"], "conversation")
        prior = []
        for m in conv["messages"]:
            at = datetime.fromisoformat(m["at"].replace("Z", "+00:00"))
            obs = Observation(source.id, m["key"], m["text"], at, ctx.id)
            clock.now = at
            memory.ingest(Batch(sources=(source,), observations=(obs,), contexts=(ctx,)))
            cset, _ = RulesV2().extract(obs, prior=tuple(prior))
            prior.append(cset)
            for k, v in form(memory, obs, cset).counts().items():
                totals[k] += v
    clock.set("2025-12-01")
    return totals


def ask(memory, conv, claim_type, roles, at, believed_at=None):
    ids = {r: referent_id("ctx:" + conv, kind, name) for r, (kind, name) in roles.items()}
    return memory.ask(claim_type, ids, utc(at), believed_at=utc(believed_at) if believed_at else None,
                      semantics="v2").answer


def test_formed_development_claims_can_be_queried(memory, formed):
    assert formed == {"formed": 7, "withheld": 0, "review": 1, "rejected": 0}
    assert len(memory.all_claims()) == 7
    tom = {"employee": ("person", "Tom Okafor"), "employer": ("organization", "Northwind")}
    dana = {"report": ("person", "Priya Shah"), "manager": ("person", "Dana Li")}
    elena = {"report": ("person", "Marco Rossi"), "manager": ("person", "Elena Petrova")}
    alice = {"report": ("person", "Alice"), "manager": ("person", "Sam")}
    assert ask(memory, "d1", "employment", tom, "2025-07-01") is Answer.FALSE            # left in May
    assert ask(memory, "d1", "reporting", dana, "2025-06-10T11:02") is Answer.TRUE       # "Since June ..., reports"
    assert ask(memory, "d1", "reporting", dana, "2025-05-15") is Answer.UNKNOWN          # since June: never FALSE before
    assert ask(memory, "d2", "reporting", elena, "2024-06-01") is Answer.TRUE            # since 2023
    assert ask(memory, "d2", "reporting", elena, "2025-06-01") is Answer.UNKNOWN         # the correction awaits review
    assert ask(memory, "d3", "reporting", alice, "2025-10-01T09:02") is Answer.TRUE
    assert ask(memory, "d1", "employment", tom, "2025-07-01", believed_at="2025-06-01") is Answer.NOT_YET_KNOWN
