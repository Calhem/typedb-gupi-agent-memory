"""D3 (docs/evaluation/phase-7b/contract-corrections.md): a correction or retraction never changes an existing
claim by itself. It always waits for review, and its suggestion never claims a target it cannot justify:
unidentified -> "missing", several plausible -> "ambiguous", a target no longer believed -> not "resolved"."""

from datetime import datetime, timedelta, timezone

import pytest

from gupi import ids
from gupi.formation import extractors, store
from gupi.formation.candidate import Candidate, CandidateSet, Participant, Passage, Relation, TimeEvidence
from gupi.records import Batch, Context, Observation, Source

pytestmark = pytest.mark.integration
START = datetime(2025, 8, 20, 9, tzinfo=timezone.utc)


class Thread:
    def __init__(self, memory, clock, context="ctx:d3"):
        self.memory, self.clock, self.context, self.prior, self.n = memory, clock, context, [], 0

    def say(self, text, version="rules:v2.1"):
        self.n += 1
        self.clock.now = START + timedelta(minutes=10 * self.n)
        obs = Observation("src:d3", f"{self.context}-{self.n}", text, self.clock.now, self.context)
        self.memory.ingest(Batch((Source("src:d3", "chat"),), (obs,), contexts=(Context(self.context, "conversation"),)))
        cset, report = extractors.get(version).extract(obs, prior=tuple(self.prior))
        self.prior.append(cset)
        self.clock.now += timedelta(minutes=1)
        if cset.candidates:
            store.submit(self.memory, obs, cset)
        return [store.get(self.memory, c.id) for c in cset.candidates], report


def nothing_changed(memory, before):
    """No supersession, no withdrawn belief: every claim believed before is still believed."""
    believed = memory.believed_ids(memory.clock())
    assert set(before) <= believed
    assert not [c for c in memory.all_claims() if c.superseded_by]


def believed_now(memory):
    return set(memory.believed_ids(memory.clock()))


def test_an_explicitly_identified_target_is_suggested_and_waits_for_review(memory, clock):
    t = Thread(memory, clock)
    (first,), _ = t.say("Nora Vance joined Halden in March 2025.")
    before = believed_now(memory)
    (fix,), _ = t.say("Correction: Nora Vance joined Halden in April 2025, not March.")
    assert first.status == "formed" and fix.status == "review"
    (s,) = fix.suggestions
    assert (s.resolution, s.targets) == ("resolved", (first.claim_id,))
    assert "Correction: Nora Vance joined Halden in April 2025, not March." in fix.payload  # the source is kept
    nothing_changed(memory, before)


def test_no_identifiable_target_is_missing_not_invented(memory, clock):
    t = Thread(memory, clock)
    (fix,), _ = t.say("Correction: Nora Vance joined Halden in April 2025.")
    assert fix.status == "review"
    (s,) = fix.suggestions
    assert (s.resolution, s.targets) == ("missing", ())
    nothing_changed(memory, set())


def test_several_plausible_targets_are_ambiguous_even_when_the_extractor_named_one(memory, clock):
    t = Thread(memory, clock)
    (a,), _ = t.say("Nora Vance joined Halden in February 2025.")
    (b,), _ = t.say("Nora Vance joined Halden in March 2025.")
    before = believed_now(memory)
    (fix,), _ = t.say("Correction: Nora Vance joined Halden in April 2025, not March.")
    assert fix.status == "review"
    (s,) = fix.suggestions
    assert s.resolution == "ambiguous" and set(s.targets) == {a.claim_id, b.claim_id}
    nothing_changed(memory, before)


def test_a_target_in_another_conversation_is_not_matched(memory, clock):
    (other,), _ = Thread(memory, clock, "ctx:d3-other").say("Nora Vance joined Halden in March 2025.")
    before = believed_now(memory)
    (fix,), _ = Thread(memory, clock, "ctx:d3-here").say("Correction: Nora Vance joined Halden in April 2025, not March.")
    assert fix.status == "review" and fix.suggestions[0].resolution == "missing"
    nothing_changed(memory, before)


def test_a_correction_about_an_unresolved_pronoun_forms_nothing(memory, clock):
    t = Thread(memory, clock)
    t.say("Nora Vance joined Halden in March 2025.")
    before = believed_now(memory)
    stored, report = t.say("Correction: She joined Halden in April 2025, not March.")
    assert stored == [] and any("unresolved reference" in r for _, r in report.rejected)
    nothing_changed(memory, before)


def test_a_superseded_target_is_not_suggested_as_resolved(memory, clock):
    t = Thread(memory, clock)
    (old,), _ = t.say("Nora Vance joined Halden in March 2025.")
    (new,), _ = Thread(memory, clock, "ctx:d3").say("Nora Vance joined Halden in February 2025.")
    clock.now += timedelta(minutes=1)
    memory.supersede(old.claim_id, new.claim_id, reason="test", decided_by="reviewer-a")
    before = believed_now(memory)
    (fix,), _ = t.say("Correction: Nora Vance joined Halden in April 2025, not March.")
    assert fix.status == "review"
    (s,) = fix.suggestions
    assert old.claim_id not in s.targets or s.resolution != "resolved"
    assert set(before) <= believed_now(memory)


def test_a_retraction_with_no_identifiable_target_waits_for_review(memory, clock):
    """An extractor's retraction whose target is not in memory (rules:v2.x cannot express retractions)."""
    text = "Retraction: Nora Vance did not join Halden."
    clock.now = START
    obs = Observation("src:d3", "r1", text, clock.now, "ctx:d3")
    memory.ingest(Batch((Source("src:d3", "chat"),), (obs,), contexts=(Context("ctx:d3", "conversation"),)))
    c = Candidate("employment", Passage(obs.id, 0, len(text), text),
                  (Participant("employee", "Nora Vance", 12, 22, "person"), Participant("employer", "Halden", 36, 42, "organization")),
                  polarity="negative", relations=(Relation("retracts", "candidate:" + "0" * 32, "stated", "Retraction:"),),
                  times=(TimeEvidence("holds-at", "did not join", 23, 35, clock.now, clock.now, "instant"),))
    clock.now += timedelta(minutes=1)
    store.submit(memory, obs, CandidateSet(obs.id, ids.content_hash(text), "test", (c,)))
    s = store.get(memory, c.id)
    assert s.status == "review" and s.suggestions[0].resolution == "missing"
    nothing_changed(memory, set())
