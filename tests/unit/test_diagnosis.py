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


def test_counts_subset_is_deterministic_and_about_five_percent():
    from gupi.benchmarks.diagnosis import counts
    keys = [f"k{i}" for i in range(4000)]
    picked = [k for k in keys if counts.in_subset("x", k)]
    assert picked == [k for k in keys if counts.in_subset("x", k)] and 120 < len(picked) < 280


def test_path_judge_keeps_attribution_and_certainty_apart():
    from gupi.benchmarks.diagnosis import pathcompare
    expect = {"type": "employment", "roles": {"employee": "Nora", "employer": "Halden"}, "times": ["start"],
              "mode": "direct", "commitment": "probable"}
    got = {"candidates": [{"type": "employment", "roles": {"employee": "Nora", "employer": "Halden"},
                           "times": [("start", "2025-03-01", "2025-04-01")], "mode": "direct", "commitment": "certain",
                           "asserted_by": None, "relations": []}]}
    assert pathcompare.judge(expect, got) == "match on type and roles; differs in commitment"
    assert pathcompare.judge(None, {"candidates": []}) == "correct (nothing)"


def test_sample_results_cover_every_annotated_fact():
    from gupi.benchmarks.diagnosis import deliverables
    import json
    rows = deliverables.results_rows()
    ann = json.loads((deliverables.DIR / "annotations.json").read_text())
    facts = sum(len(t["facts"]) for v in ann["datasets"].values() for ts in v.values() for t in ts)
    assert sum(r["category"] != "C" for r in rows) == facts == 85
    assert all("text" not in r for r in rows)
