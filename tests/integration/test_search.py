"""Keyword search over source text (the baseline), on the live server."""

import pytest
from helpers import CHAT, HR, PEOPLE, observe, utc

from gupi.records import Batch
from gupi.search import tokens

pytestmark = pytest.mark.integration

TEXTS = [
    ("hr-1", "Alice reports to Bob.", "2025-01-05", HR),
    ("hr-2", "Alice left Acme in May.", "2025-06-01", HR),
    ("c-1", "Bobby likes coffee.", "2025-01-06", CHAT),
    ("c-2", "ALICE and BOB met Acme's CTO.", "2025-07-01", CHAT),
]


@pytest.fixture
def corpus(memory, clock):
    for key, text, when, src in TEXTS:
        clock.set(when)  # received when said
        memory.ingest(Batch((src,), (observe(src, key, text, when),), PEOPLE))
    return memory


def test_ranking_whole_words_case_and_as_of(corpus):
    hits = corpus.search("Did Alice report to Bob?", believed_at=utc("2025-12-01"))
    # Both match "alice" and "bob" ("report" does not match "reports": no stemming); the shorter text ranks first.
    assert [h.content for h in hits][:2] == ["Alice reports to Bob.", "ALICE and BOB met Acme's CTO."]
    assert all("bobby" not in h.content.lower() for h in hits)  # "bob" inside "Bobby" is not a match
    early = corpus.search("Alice Bob", believed_at=utc("2025-03-01"))
    assert [h.content for h in early] == ["Alice reports to Bob."]  # later messages were not yet received
    assert corpus.search("the of and") == []


def test_tokens_drop_stopwords():
    assert tokens("Who was Halden's CTO in March?") == ["halden's", "cto", "march"]
