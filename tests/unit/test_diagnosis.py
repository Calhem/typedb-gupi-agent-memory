"""Phase 7A diagnosis helpers that need no TypeDB or datasets."""

from gupi.benchmarks.diagnosis import audit, sample


def test_why_no_pattern_readings():
    assert audit.why_no_pattern("My team works at the hospital") == "the subject is a pronoun or possessive"
    assert audit.why_no_pattern("I work at a hospital").startswith("no capitalised name")
    assert audit.why_no_pattern("Welcome Jonas Berg, who joined Lumen Labs in 2025, to the team").startswith(
        "a supported phrase inside a longer clause")


def test_sampling_is_seeded_and_stratified():
    turns = [{"key": f"k{i}", "chars": i, "g": i % 2, "_text": "my job" if i % 3 == 0 else "hello"} for i in range(60)]
    cuts, chosen = sample.draw("x", turns, lambda t: t["g"], 2)
    assert len(chosen) == 12 and chosen == sample.draw("x", turns, lambda t: t["g"], 2)[1]
    assert sample.draw("y", turns, lambda t: t["g"], 2)[1] != chosen      # the dataset name is part of the seed
    pool, tgt = sample.targeted("x", turns, {t["key"] for t in chosen}, 5)
    assert all(sample.WORK.search(t["_text"]) for t in tgt) and not {t["key"] for t in tgt} & {t["key"] for t in chosen}
