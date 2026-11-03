"""Scoped evidence retrievers (keyword, embedding, structured, hybrid) on the live server."""

import pytest
from helpers import CHAT, utc
from test_vectors import BagOfWords

from gupi import evidence, vectors
from gupi.records import Batch, Context, Observation, Referent

pytestmark = pytest.mark.integration

S1, S2, OTHER = Context("s:1", "session"), Context("s:2", "session"), Context("s:x", "session")
SPEAKERS = (Referent("p:mel", "person", "Melanie"), Referent("p:car", "person", "Caroline"))


@pytest.fixture
def chat(memory, clock):
    turns = [
        (S1, "t1", "I went running this morning.", "2023-05-08", "p:mel"),
        (S1, "t2", "Nice! I had coffee with my mum.", "2023-05-08", "p:car"),
        (S2, "t3", "Chess club starts again in June.", "2023-06-20", "p:mel"),
        (S2, "t4", "Caroline, did you try the new coffee place?", "2023-06-20", "p:mel"),
        (OTHER, "t5", "Coffee coffee coffee.", "2023-06-21", "p:car"),
    ]
    obs = [Observation(CHAT.id, k, text, utc(day), ctx.id, author_id=who) for ctx, k, text, day, who in turns]
    memory.ingest(Batch((CHAT,), tuple(obs), SPEAKERS, contexts=(S1, S2, OTHER)))
    vectors.store(memory, BagOfWords(), [S1.id, S2.id, OTHER.id])
    return {o.record_key: o.id for o in obs}


SCOPE = [S1.id, S2.id]


def test_keyword_and_embedding_stay_in_scope(memory, chat):
    kw = evidence.keyword(memory, "coffee", SCOPE).ids
    assert set(kw) == {chat["t2"], chat["t4"]}  # t5 is outside the scope
    em = evidence.embedding(memory, BagOfWords(), "coffee", SCOPE, k=2).ids
    assert set(em) == {chat["t2"], chat["t4"]}
    assert evidence.embedding(memory, None, "coffee", SCOPE).ids == []  # offline mode without embeddings


def test_structured_uses_authorship_names_and_time_windows(memory, chat):
    r = evidence.structured(memory, "What did Caroline drink?", SCOPE, asked_at=utc("2023-07-01"))
    assert r.notes["entities"] == ["Caroline"]
    assert set(r.ids) == {chat["t2"], chat["t4"]}          # said by Caroline, or naming her
    assert r.ids[0] == chat["t4"]                          # newest first (no claims here)
    june = evidence.structured(memory, "What did Melanie start in June?", SCOPE, asked_at=utc("2023-07-01"))
    assert june.notes["window"][0] == utc("2023-06-01") and set(june.ids) == {chat["t3"], chat["t4"]}
    nobody = evidence.structured(memory, "What is chess?", SCOPE)
    assert nobody.ids == [] and "no entity" in nobody.notes["reason"]


def test_hybrid_fuses_and_filters_by_structure(memory, chat):
    r = evidence.hybrid(memory, BagOfWords(), "What coffee did Caroline have?", SCOPE, asked_at=utc("2023-07-01"))
    assert r.notes["filtered_by_structure"] and set(r.ids) <= {chat["t2"], chat["t4"]}
    open_q = evidence.hybrid(memory, BagOfWords(), "Who likes chess?", SCOPE)
    assert not open_q.notes["filtered_by_structure"] and open_q.ids[0] == chat["t3"]
