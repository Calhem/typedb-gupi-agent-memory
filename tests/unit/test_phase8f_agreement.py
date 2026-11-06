"""The agreement measures on invented ledgers: no conversation, no reader output."""

from gupi.benchmarks import phase8f_agreement as g

TEXT = {"D1:1": "I started learning to sail last spring.", "D1:2": "Sold my boat today.", "D2:1": "I sail on Sundays.", "D2:2": "My kiln arrived.",
        "D3:1": "I fired my first pot.", "D3:2": "I am not sailing now."}
WHO = {k: "Juno" for k in TEXT}


def mention(turn, quote, role="engagement", link="clear", time=None):
    return {"turn": turn, "quote": quote, "role": role, "link": link, "time": time}


def activity(i, *mentions, state="unknown", person="Juno"):
    return {"id": i, "person": person, "label": i, "basis": "explicit", "final_state": state, "mentions": list(mentions)}


SAIL = [mention("D1:1", "I started learning to sail", "start"), mention("D2:1", "I sail on Sundays"), mention("D3:2", "I am not sailing now", "negated")]
POT = [mention("D2:2", "My kiln arrived", "event"), mention("D3:1", "I fired my first pot", "event")]
ONE = {"activities": [activity("a", *SAIL), activity("b", *POT)], "contradictions": [{"activities": ["a"], "turns": ["D2:1", "D3:2"]}]}


def test_identical_ledgers_with_different_ids_agree_fully():
    other = {"activities": [activity("x", *SAIL), activity("y", *POT)], "contradictions": [{"activities": ["x"], "turns": ["D3:2"]}]}
    r = g.compare(ONE, other, TEXT, WHO)
    assert r["mention_f1"] == 1.0 and r["activity_f1"] == 1.0 and r["adjusted_rand"] == 1.0 and r["bcubed"] == (1.0, 1.0, 1.0)
    assert r["role_kappa"] == 1.0 and r["final_state_agree"] == 1.0 and r["contradictions_shared"] == 1 and r["merge_rate"] == 0


def test_overlapping_quotes_of_different_lengths_match():
    short = {"activities": [activity("x", mention("D1:1", "learning to sail", "start"))]}
    long = {"activities": [activity("y", mention("D1:1", "I started learning to sail last spring", "start"))]}
    assert g.compare(short, long, TEXT, WHO)["matched"] == 1


def test_a_merge_lowers_grouping_agreement_and_is_named():
    merged = {"activities": [activity("m", *SAIL, *POT)]}
    r = g.compare(ONE, merged, TEXT, WHO)
    assert r["mention_f1"] == 1.0 and r["adjusted_rand"] < 0.5 and r["bcubed"][0] < 1 and r["bcubed"][1] == 1.0
    assert r["merged_by_second"] == 1 and r["merged_by_first"] == 0


def test_a_split_is_seen_from_the_other_side():
    r = g.compare({"activities": [activity("m", *SAIL, *POT)]}, ONE, TEXT, WHO)
    assert r["merged_by_first"] == 1 and r["merged_by_second"] == 0


def test_kappa_corrects_for_chance():
    assert g.kappa(list("aabb"), list("aabb")) == 1.0
    assert g.kappa(list("aabb"), list("abab")) == 0.0
    assert g.kappa(list("aaaa"), list("aaaa")) is None and g.kappa([], []) is None


def test_adjusted_rand_ignores_label_names_and_handles_edges():
    assert g.adjusted_rand([1, 1, 2, 2], ["x", "x", "y", "y"]) == 1.0
    assert g.adjusted_rand([1], ["x"]) is None
    assert g.adjusted_rand([1, 1, 1, 1], [1, 2, 3, 4]) <= 0.0001


def test_evidence_problems_are_counted_not_repaired():
    bad = {"activities": [activity("a", mention("D1:1", "I never said this"), mention("D9:9", "x"), mention("D2:1", "I sail", "dreamt"),
                          mention("D2:1", "I sail", time="in 1999"))]}
    count, total, why = g.problems(bad, TEXT, WHO)
    assert (count, total) == (4, 4) and set(why) == {"quote not in that turn", "no such turn", "unknown role or link", "time words not in that turn"}
    assert g.units(bad, TEXT, WHO)[0].quote == "I sail"


def test_another_persons_words_are_invalid():
    other = dict(WHO, **{"D1:1": "Bram"})
    assert g.problems({"activities": [activity("a", SAIL[0])]}, TEXT, other)[2] == {"another person's words": 1}


def test_continuity_from_silence_is_found():
    still = {"activities": [activity("a", SAIL[0], state="engaged"), activity("b", SAIL[2], state="engaged"), activity("c", SAIL[0])]}
    assert g.invented_continuity(still, "D3") == ["a"]


def test_consensus_scores_only_what_both_readers_agree_on():
    other = {"activities": [activity("x", *SAIL), activity("y", *POT)]}
    good = g.consensus(ONE, other, {"activities": [activity("p", *SAIL), activity("q", *POT)]}, TEXT, WHO)
    assert good["link_recall"] == 1.0 and good["false_merge_rate"] == 0 and good["mention_recall"] == 1.0
    merged = g.consensus(ONE, other, {"activities": [activity("m", *SAIL, *POT)]}, TEXT, WHO)
    assert merged["false_merge_rate"] == 1.0


def test_correction_share_counts_what_would_have_to_change():
    assert g.correction_share({"activities": (4, 4), "aligned": 3, "merged_by_second": 1}) == 0.5


def test_a_computed_state_ignores_what_the_reader_said_about_the_ending():
    from datetime import datetime, timedelta, timezone
    said = {k: datetime(2023, 1, 1, tzinfo=timezone.utc) + timedelta(days=i * 30) for i, k in enumerate(TEXT)}
    still = {"activities": [activity("a", mention("D2:1", "I sail on Sundays"), state="engaged")]}
    end = max(said.values()) + timedelta(days=1)
    assert g.computed_states(still, said, WHO, end) == {"a": "unknown"}


def test_only_large_activities_are_kept_when_asked():
    assert [a["id"] for a in g.large_only(ONE, 3)["activities"]] == ["a"]
