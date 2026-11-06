"""The ordering rules of gupi.paths, without a database. Synthetic ids only."""

from gupi.paths import Budget, interleave, named_speaker, nearby, speaker_first, with_neighbours


def session(*turns):
    return {t: list(turns) for t in turns}, {t: i for i, t in enumerate(turns)}


def test_neighbours_stay_inside_the_session_and_are_nearest_first():
    seq, pos = session("a", "b", "c", "d", "e")
    assert nearby("c", seq, pos, 1) == ["d", "b"]
    assert nearby("c", seq, pos, 2) == ["d", "b", "e", "a"]
    assert nearby("a", seq, pos, 1) == ["b"]        # no turn before the first
    assert nearby("e", seq, pos, 1) == ["d"]


def test_top_hits_keep_their_place_and_each_later_hit_brings_its_neighbours():
    seq, pos = session("a", "b", "c", "d", "e", "f")
    assert with_neighbours(["c", "f"], seq, pos, keep=1, window=1) == ["c", "d", "b", "f", "e"]
    assert with_neighbours(["c", "f"], seq, pos, keep=2, window=1)[:2] == ["c", "f"]


def test_neighbours_never_cross_a_session():
    seq, pos = session("a", "b")
    other, other_pos = session("x", "y")
    seq.update(other); pos.update(other_pos)
    assert set(with_neighbours(["b"], seq, pos, keep=1, window=1)) == {"a", "b"}


def test_the_speaker_orders_but_never_filters():
    assert speaker_first(["a", "b", "c"], {"b"}) == ["b", "a", "c"]
    assert speaker_first(["a", "b"], set()) == ["a", "b"]
    assert sorted(speaker_first(["a", "b", "c"], {"z"})) == ["a", "b", "c"]


def test_interleaving_keeps_the_earliest_place_and_no_duplicates():
    assert interleave(["a", "b", "c"], ["a", "c", "d"]) == ["a", "b", "c", "d"]


def test_a_speaker_counts_only_when_exactly_one_is_named():
    labels = {"Kim": frozenset({"p:1"}), "Sam": frozenset({"p:2"})}
    assert named_speaker("What did Kim do?", labels) == frozenset({"p:1"})
    assert named_speaker("Did Kim meet Sam?", labels) == frozenset()
    assert named_speaker("What happened?", labels) == frozenset()
    assert named_speaker("What did Kimberly do?", labels) == frozenset()   # whole words only


def test_ordering_is_deterministic():
    seq, pos = session("a", "b", "c", "d")
    runs = [with_neighbours(["c", "a"], seq, pos, 1, 1) for _ in range(3)]
    assert runs[0] == runs[1] == runs[2]


def test_the_default_budget_is_conservative():
    b = Budget()
    assert (b.k, b.keep, b.window) == (10, 3, 1)
