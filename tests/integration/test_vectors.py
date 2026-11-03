"""Embeddings stored in TypeDB and searched within a scope. Uses a deterministic stand-in embedder, so it runs
without the optional embeddings extra; the real model is exercised by the Phase 5 benchmarks."""

import pytest
from helpers import CHAT, PEOPLE, utc

from gupi import vectors
from gupi.records import Batch, Context, Observation
from gupi.typedb.connection import transaction
from typedb.driver import TransactionType

pytestmark = pytest.mark.integration

WORDS = ["coffee", "tea", "running", "chess"]


class BagOfWords:
    """A deterministic stand-in for a real model: one dimension per word."""
    model = "test:bag-of-words"
    dimension = len(WORDS) + 1

    def __init__(self):
        self.calls = 0

    def embed(self, texts):
        self.calls += len(texts)
        return [[float(w in t.lower()) for w in WORDS] + [0.1] for t in texts]


def test_store_is_idempotent_and_search_respects_scope(memory, clock):
    a, b = Context("conv:a", "conversation"), Context("conv:b", "conversation")
    obs = [Observation(CHAT.id, "a1", "I love coffee in the morning.", utc("2025-01-01"), a.id),
           Observation(CHAT.id, "a2", "Chess club is on Tuesdays.", utc("2025-01-02"), a.id),
           Observation(CHAT.id, "b1", "Coffee again, obviously.", utc("2025-01-03"), b.id)]
    memory.ingest(Batch((CHAT,), tuple(obs), PEOPLE, contexts=(a, b), ))
    embedder = BagOfWords()
    assert vectors.store(memory, embedder, [a.id, b.id]) == 3
    assert vectors.store(memory, embedder, [a.id, b.id]) == 0 and embedder.calls == 3  # nothing re-embedded
    hits = vectors.search(memory, embedder, "coffee?", [a.id], k=2)
    assert [h for h, _ in hits][0] == obs[0].id and obs[2].id not in [h for h, _ in hits]
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        assert len(vectors.vectors_in(tx, [a.id, b.id], embedder.model)) == 3


def test_authorship_is_recorded(memory):
    a = Context("conv:c", "conversation")
    o = Observation(CHAT.id, "c1", "Hello from Alice.", utc("2025-01-01"), a.id, author_id="p:alice")
    memory.ingest(Batch((CHAT,), (o,), PEOPLE, contexts=(a,)))
    from gupi import typeql
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        rows = typeql.concept_rows(tx, 'match authorship (author: $a, authored: $o); $a has gupi-id "p:alice";')
    assert len(rows) == 1
    with pytest.raises(ValueError, match="unknown author"):
        memory.ingest(Batch((CHAT,), (Observation(CHAT.id, "c2", "Hi", None, a.id, author_id="p:nobody"),)))
