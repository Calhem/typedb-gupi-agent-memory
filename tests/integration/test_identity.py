"""Suggested identities: proposed as hypotheses, merged only once accepted, split again when retracted."""

import pytest
from helpers import utc

from gupi.conflicts import DIFFERING
from gupi.extraction.pipeline import extract
from gupi.extraction.rules import RuleExtractor
from gupi.records import Batch, Context, Observation, Source
from gupi.status import Status

pytestmark = pytest.mark.integration

CHAT = Source("src:team", "conversation")
A, B = Context("conv:a", "conversation"), Context("conv:b", "conversation")
MESSAGES = [
    Observation(CHAT.id, "a-1", "Priya Shah joined Northwind as Head of Data in January 2025.", utc("2025-03-03"), A.id),
    Observation(CHAT.id, "a-2", "Priya reports to Tom Okafor.", utc("2025-03-03T09:05"), A.id),
    Observation(CHAT.id, "b-1", "Priya Shah works at Northwind as a Director.", utc("2025-06-10"), B.id),
]


@pytest.fixture
def extracted(memory, clock):
    clock.set("2025-06-11")
    memory.ingest(Batch((CHAT,), tuple(MESSAGES), contexts=(A, B)))
    result = extract(memory, RuleExtractor(), MESSAGES)
    memory.review_many([(c, "accepted") for c in result.claims], "reviewer")  # accept what was extracted
    return memory


def by_reason(suggestions, text):
    return [s for s in suggestions if text in s.reason]


def test_suggestions_are_hypotheses_with_reasons_and_are_not_repeated(extracted, clock):
    clock.set("2025-06-12")
    found = extracted.suggest_identities()
    assert {s.reason for s in found} == {
        "same name 'Priya Shah' in different conversations",
        "same name 'Northwind' in different conversations",
        "'Priya' and 'Priya Shah': first name matches a full name in the same conversation",
    }
    identities = [c for c in extracted.all_claims() if c.type == "identity"]
    assert len(identities) == 3
    for c in identities:
        assert c.status_at(clock()) is Status.HYPOTHESIS and c.basis == "inferred" and c.method == "identity:suggest:v1"
        assert {e.quote for e in c.evidence} <= {"Priya Shah", "Priya", "Northwind"}
    assert extracted.suggest_identities() == []  # already considered, whatever the outcome


def test_accepting_merges_from_then_on_and_retracting_splits_again(extracted, clock):
    clock.set("2025-06-12")
    found = extracted.suggest_identities()
    ids = {c.values["reason"]: c.id for c in extracted.all_claims() if c.type == "identity"}
    same_person = ids[by_reason(found, "'Priya Shah' in different")[0].reason]
    same_org = ids[by_reason(found, "'Northwind' in different")[0].reason]
    b_claim = next(c for c in extracted.all_claims() if c.type == "employment" and "Director" in c.values.values())
    roles = {k: v[0] for k, v in b_claim.roles.items()}

    def considered(at):
        return {c.values.get("job-title") for c in extracted.ask("employment", roles, utc("2025-05"), believed_at=at).considered}

    assert considered(utc("2025-06-12")) == {"Director"}                   # separate until accepted
    assert extracted.conflicts() == []
    clock.set("2025-06-13")
    extracted.review_many([(same_person, "accepted"), (same_org, "accepted")], "reviewer")
    assert considered(utc("2025-06-14")) == {"Director", "Head of Data"}   # merged in answers from now on
    titles = [x for x in extracted.conflicts() if x.kind == DIFFERING]
    assert titles and "job-title" in titles[0].reason                      # the two titles now meet

    clock.set("2025-07-01")
    extracted.review(same_person, "retracted", "reviewer", reason="different people")
    assert considered(utc("2025-07-02")) == {"Director"}                   # split again
    assert considered(utc("2025-06-20")) == {"Director", "Head of Data"}   # history of what was believed is kept
