"""ClaudeExtractor with a simulated client: request shape, budget enforcement and failure handling.

No network calls and no spending: the client is a stand-in that records what it was asked.
"""

import json
import uuid
from types import SimpleNamespace as NS

import pytest
from helpers import CHAT, Clock, utc

from gupi.budget import BudgetExceeded, Ledger, LedgerError
from gupi.extraction.claude import MODEL, ClaudeExtractor
from gupi.extraction.pipeline import extract
from gupi.records import Batch, Context, Observation
from gupi.status import Status

pytestmark = pytest.mark.integration

CONVO = Context("conv:c", "conversation")
TEXT = "Kim has worked at Vector since 2022. She mentors two interns."
MSG = Observation(CHAT.id, "c-1", TEXT, utc("2025-11-03T12:00"), context_id=CONVO.id)
OUTPUT = {
    "mentions": [{"id": "m1", "text": "Kim", "kind": "person"}, {"id": "m2", "text": "Vector", "kind": "organization"}],
    "claims": [
        {"type": "employment", "roles": [{"role": "employee", "mention": "m1"}, {"role": "employer", "mention": "m2"}],
         "values": [], "predicate": "", "object_text": "", "quote": "Kim has worked at Vector since 2022.",
         "basis": "explicit", "confidence": 0.9, "time": {"start": "since 2022", "end": "", "ongoing": True}},
        {"type": "statement", "roles": [{"role": "subject", "mention": "m1"}], "values": [], "predicate": "mentors",
         "object_text": "two interns", "quote": "She mentors two interns.", "basis": "inferred", "confidence": 0.6,
         "time": {"start": "", "end": "", "ongoing": True}},
    ]}


def response(payload=OUTPUT, stop="end_turn", iterations=None, model=MODEL):
    usage = NS(input_tokens=1200, output_tokens=900, cache_creation_input_tokens=0, cache_read_input_tokens=0,
               iterations=iterations)
    return NS(stop_reason=stop, model=model, usage=usage,
              content=[NS(type="thinking", thinking=""), NS(type="text", text=json.dumps(payload))])


class FakeClient:
    def __init__(self, reply, ledger=None):
        self.reply, self.ledger, self.requests, self.spent_during_call = reply, ledger, [], []
        self.beta = NS(messages=NS(create=self.create))

    def create(self, **params):
        self.requests.append(params)
        if self.ledger:
            self.spent_during_call.append(self.ledger.spent_microusd())
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


@pytest.fixture
def ledger(driver):
    name = f"gupi-test-ledger-{uuid.uuid4().hex[:8]}"
    yield Ledger(driver, name, limit_usd=10.0, clock=Clock())
    driver.databases.get(name).delete()


@pytest.fixture
def ingested(memory):
    memory.ingest(Batch((CHAT,), (MSG,), contexts=(CONVO,)))
    return memory


def test_request_shape_reservation_first_and_hypotheses_out(ingested, ledger, clock):
    client = FakeClient(response(), ledger)
    result = extract(ingested, ClaudeExtractor(client, ledger), [MSG])

    (req,) = client.requests
    assert req["model"] == "claude-opus-5-5" and req["max_tokens"] == 8000
    assert req["output_config"]["format"]["type"] == "json_schema" and req["output_config"]["effort"] == "medium"
    assert req["fallbacks"] == "default" and req["betas"] == ["server-side-fallback-2026-07-01"]
    assert "temperature" not in req and "thinking" not in req
    assert client.spent_during_call[0] > 0  # the worst case was reserved before the request went out
    assert ledger.spent_microusd() == 1200 * 4 + 900 * 20  # then settled at Opus 5.5 prices: $0.0228

    views = [ingested.claim(c) for c in result.claims]
    assert {(v.type, v.basis) for v in views} == {("employment", "explicit"), ("statement", "inferred")}
    assert all(v.status_at(clock()) is Status.HYPOTHESIS for v in views)
    employment = next(v for v in views if v.type == "employment")
    assert employment.valid.from_earliest == utc("2022-01-01") and employment.valid_to_basis == "ongoing-at-observation"


def test_budget_refuses_before_anything_is_sent(ingested, driver):
    name = f"gupi-test-ledger-{uuid.uuid4().hex[:8]}"
    tiny = Ledger(driver, name, limit_usd=0.01, clock=Clock())
    try:
        client = FakeClient(response())
        with pytest.raises(BudgetExceeded):
            extract(ingested, ClaudeExtractor(client, tiny), [MSG])
        assert client.requests == [] and tiny.spent_microusd() == 0
    finally:
        driver.databases.get(name).delete()


def test_refusal_and_truncation_produce_no_claims_but_are_charged(ingested, ledger):
    result = extract(ingested, ClaudeExtractor(FakeClient(response(stop="refusal")), ledger), [MSG])
    assert result.claims == [] and ("output", "refusal") in [(w, r) for _, w, r in result.rejected]
    assert ledger.spent_microusd() == 22_800


def test_fallback_attempts_are_charged_per_model(ingested, ledger):
    iterations = [NS(type="message", model=MODEL, input_tokens=1200, output_tokens=0,
                     cache_creation_input_tokens=0, cache_read_input_tokens=0),
                  NS(type="fallback_message", model="claude-opus-4-8", input_tokens=1200, output_tokens=900,
                     cache_creation_input_tokens=0, cache_read_input_tokens=0)]
    extract(ingested, ClaudeExtractor(FakeClient(response(iterations=iterations, model="claude-opus-4-8")), ledger), [MSG])
    assert ledger.spent_microusd() == 1200 * 4 + (1200 * 5 + 900 * 25)


def test_network_failure_keeps_the_reservation_and_allows_a_retry(ingested, ledger):
    failing = ClaudeExtractor(FakeClient(ConnectionError("network down")), ledger)
    with pytest.raises(ConnectionError):
        extract(ingested, failing, [MSG])
    held = ledger.spent_microusd()
    assert held > 0  # unknown outcome: counted as spent (fail closed)
    retry = extract(ingested, ClaudeExtractor(FakeClient(response()), ledger), [MSG])
    assert len(retry.claims) == 2 and retry.skipped == []  # nothing was recorded for the failed attempt


def test_unknown_model_cannot_be_called(ingested, ledger):
    client = FakeClient(response())
    with pytest.raises(LedgerError, match="no price"):
        extract(ingested, ClaudeExtractor(client, ledger, model="claude-imaginary-1"), [MSG])
    assert client.requests == []
