"""Conversational retrieval against a live TypeDB. Synthetic, developer-authored text."""

from datetime import datetime, timedelta, timezone

import pytest

from gupi import evidence, paths
from gupi.records import Batch, Context, Observation, Referent, Source

pytestmark = pytest.mark.integration
T0 = datetime(2025, 3, 1, 9, tzinfo=timezone.utc)
KIM, SAM = Referent("p:kim", "person", "Kim"), Referent("p:sam", "person", "Sam")
SOURCE = Source("src:c", "conversation")
TURNS = [(SAM, "Have you picked up any new hobby lately?"),
         (KIM, "Yes, pottery, and it has been wonderful."),
         (SAM, "Nice. Mine is still the sailing club."),
         (KIM, "I also started a pottery class downtown."),
         (SAM, "Which day do you go?"),
         (KIM, "Every Tuesday evening.")]


def ingest(memory, clock, turns=TURNS, session="ctx:one"):
    obs = tuple(Observation(SOURCE.id, f"{session}:{i}", text, T0 + timedelta(seconds=i), session, who.id)
                for i, (who, text) in enumerate(turns))
    clock.now = T0 + timedelta(minutes=30)
    memory.ingest(Batch((SOURCE,), obs, (KIM, SAM), contexts=(Context(session, "session"),)))
    return [o.id for o in obs]


def test_a_neighbour_supplies_what_the_words_miss(memory, clock):
    ids = ingest(memory, clock)
    q = "Which day is the pottery class?"
    assert ids[5] not in evidence.keyword(memory, q, ["ctx:one"]).ids    # "Every Tuesday evening." shares no word
    found = memory.retrieve(q, ["ctx:one"], paths.Budget(k=6))
    by_id = {i.observation_id: i for i in found.items}
    assert ids[5] in by_id and by_id[ids[5]].reasons[0] == "neighbour"


def test_keyword_hits_keep_their_provenance_and_nothing_is_duplicated(memory, clock):
    ingest(memory, clock)
    found = memory.retrieve("pottery class", ["ctx:one"], paths.Budget(k=6))
    assert len(found.ids) == len(set(found.ids))
    assert all(i.tier == "passage" and i.reasons[0] in ("keyword", "neighbour") for i in found.items)
    assert found.items[0].reasons[0] == "keyword"


def test_a_named_speaker_never_removes_the_other_speakers_turns(memory, clock):
    ids = ingest(memory, clock)
    found = memory.retrieve("Did Kim mention the sailing club?", ["ctx:one"], paths.Budget(k=6))
    assert ids[2] in found.ids                # Sam said it: a question naming the wrong speaker still finds it


def test_the_budget_is_a_hard_limit_and_truncation_is_reported(memory, clock):
    ingest(memory, clock)
    found = memory.retrieve("pottery class", ["ctx:one"], paths.Budget(k=1))
    assert len(found.ids) == 1 and found.truncated == ["k"]


def test_identical_input_gives_identical_output(memory, clock):
    ingest(memory, clock)
    runs = [memory.retrieve("pottery class Tuesday", ["ctx:one"]).items for _ in range(3)]
    assert runs[0] == runs[1] == runs[2]


def test_scope_is_respected(memory, clock):
    ingest(memory, clock)
    other = ingest(memory, clock, [(KIM, "My pottery kiln broke.")], "ctx:two")
    assert other[0] not in memory.retrieve("pottery", ["ctx:one"]).ids


def test_nothing_received_after_the_belief_time_is_returned(memory, clock):
    first = ingest(memory, clock)
    later = T0 + timedelta(minutes=30)
    clock.now = later + timedelta(days=1)
    obs = Observation(SOURCE.id, "late", "A late note about the pottery class.", clock.now, "ctx:one", KIM.id)
    memory.ingest(Batch((SOURCE,), (obs,), (KIM,), contexts=(Context("ctx:one", "session"),)))
    assert obs.id in memory.retrieve("pottery class", ["ctx:one"]).ids
    earlier = memory.retrieve("pottery class", ["ctx:one"], believed_at=later)
    assert obs.id not in earlier.ids and first[3] in earlier.ids


def test_no_hits_returns_nothing_and_says_so(memory, clock):
    ingest(memory, clock)
    found = memory.retrieve("xylophone", ["ctx:one"])
    assert found.ids == [] and found.steps == ["keyword: no hits"]
