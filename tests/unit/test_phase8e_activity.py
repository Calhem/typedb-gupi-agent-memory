"""The temporary activity model on invented activities: every state comes from the real classifier. No database."""

import json
from datetime import datetime, timedelta, timezone

from gupi.benchmarks.phase8e_activity import Activity, Mention, check, load, relationship, resumed, status, trajectory, unreconciled, word_matches


def d(m, day=1):
    return datetime(2023, m, day, 12, tzinfo=timezone.utc)


def said(key, role, month, day=1, **k):
    return Mention(key, "x", role, d(month, day), **k)


def activity(*mentions, kind="interest"):
    return Activity("A", "Juno", kind, tuple(mentions), "kiln")


def test_said_once_it_is_confirmed_then_and_only_then():
    a = activity(said("t1", "engagement", 3))
    assert status(a, d(3))[0] == "confirmed"
    assert status(a, d(3) + timedelta(days=1))[0] == "unknown"


def test_mentioned_twice_is_not_a_period():
    a = activity(said("t1", "engagement", 3), said("t2", "engagement", 6))
    assert status(a, d(4, 15))[0] == "unknown"


def test_a_stated_start_and_a_later_mention_are_presumed_between():
    a = activity(said("t1", "start", 3, time="in March"), said("t2", "engagement", 6))
    assert status(a, d(4, 15))[0] == "presumed"
    assert status(a, d(6))[0] == "confirmed"


def test_silence_after_a_start_says_nothing():
    a = activity(said("t1", "start", 3, time="in March"))
    assert status(a, d(9))[0] == "unknown"


def test_a_stated_end_is_ended_and_said_to_be_a_default():
    a = activity(said("t1", "start", 3, time="in March"), said("t2", "end", 6, time="in June"))
    assert status(a, d(9))[0] == "ended"


def test_resumption_needs_a_stated_restart():
    stopped = said("t1", "start", 3, time="in January"), said("t2", "end", 6, time="in June")
    back = activity(*stopped, said("t3", "resume", 9, time="in September"))
    assert resumed(back) and status(back, d(8))[0] == "ended"
    assert status(back, d(10))[0] == "unknown"           # back, but nothing says it is still going
    reappears = activity(*stopped, said("t3", "reference", 9))
    assert not resumed(reappears) and status(reappears, d(10))[0] == "ended"


def test_a_contradiction_is_not_a_story():
    a = activity(said("t1", "engagement", 3), said("t2", "negated", 6), said("t3", "engagement", 9))
    assert [status(a, d(m))[0] for m in (3, 6, 9)] == ["confirmed", "ended", "confirmed"]
    assert not resumed(a)                                # it flips, and nothing here calls that stopping and restarting
    assert unreconciled(a) == 2 and relationship(a) == "contradictory"


def test_relationship_comes_from_the_evidence():
    assert relationship(activity(said("t1", "plan", 3), said("t2", "event", 4))) == "unknown"
    assert relationship(activity(said("t1", "engagement", 3))) == "established"
    assert relationship(activity(said("t1", "past", 3))) == "ended"


def test_a_word_match_stays_with_its_speaker():
    from types import SimpleNamespace as NS
    claim = lambda text, obs: NS(values={"object-text": text}, evidence=(NS(observation_id=obs),))
    claims = [claim("a new kiln", "o1"), claim("her kiln", "o2"), claim("a boat", "o3")]
    assert word_matches(activity(), claims, {"o1": "Juno", "o2": "Bram", "o3": "Juno"}) == claims[:1]


def test_only_clear_mentions_count():
    a = activity(said("t1", "start", 3, time="in March", same="probable"), said("t2", "engagement", 6, same="unclear"))
    assert a.used() == [] and status(a, d(6))[0] == "unknown"


def test_plans_and_events_are_not_engagement():
    a = activity(said("t1", "plan", 3), said("t2", "event", 4), said("t3", "reference", 5))
    assert status(a, d(5))[0] == "unknown"


def test_only_what_was_said_by_then_counts():
    a = activity(said("t1", "engagement", 3), said("t2", "end", 6, time="in June"))
    assert status(a, d(7), believed_at=d(5))[0] == "unknown" and status(a, d(7))[0] == "ended"


def test_a_correction_replaces_without_erasing():
    wrong = said("t1", "end", 3, time="in March")
    fixed = said("t2", "engagement", 6, replaces="t1")
    a = activity(wrong, fixed)
    assert a.used() == [fixed] and wrong in a.mentions
    assert status(a, d(6))[0] == "confirmed"


def test_the_deciding_evidence_is_named():
    a = activity(said("t1", "engagement", 3))
    assert status(a, d(3))[1] == ("t1:engagement",)


def test_an_unreadable_start_gives_no_date():
    a = activity(said("t1", "start", 3, time="back in the day"), said("t2", "engagement", 6))
    assert status(a, d(1))[0] == "unknown" and status(a, d(6))[0] == "confirmed"


def test_a_trajectory_shows_only_changes():
    a = activity(said("t1", "start", 3, time="in March"), said("t2", "engagement", 6), said("t3", "end", 9, time="in September"))
    assert trajectory(a, [d(1), d(4), d(5), d(6), d(8), d(11)]) == ["unknown", "engaged", "ended"]


def test_ledger_quotes_must_be_real_and_spoken_by_that_person(tmp_path):
    f = tmp_path / "l.json"
    f.write_text(json.dumps({"activities": [{"id": "A", "person": "Juno", "kind": "interest", "mentions": [
        {"turn": "t1", "quote": "I fired a pot", "role": "event"}, {"turn": "t2", "quote": "missing", "role": "event"}]}]}))
    activities, _ = load(f, {"t1": d(3), "t2": d(4)})
    texts = {"t1": "I fired a pot.", "t2": "Hello."}
    assert check(activities, texts, {"t1": "Juno", "t2": "Juno"}) == ["A t2: the quote is not in that turn"]
    assert "not said by" in check(activities, texts, {"t1": "Bram", "t2": "Juno"})[0]
