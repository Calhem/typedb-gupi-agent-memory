from datetime import datetime, timezone

import pytest

from gupi.benchmarks import common, locomo, longmemeval


def test_metrics_and_unit_ranking():
    m = common.metrics(["a", "b", "c", "d"], {"b", "x"})
    assert m["recall@1"] == 0 and m["recall@5"] == 0.5 and m["hit@5"] == 1.0 and m["mrr"] == 0.5
    assert common.rank_units(["t1", "t2", "t3", "t4"], {"t1": "s1", "t2": "s1", "t3": "s2"}) == ["s1", "s2"]


def test_date_formats():
    assert locomo.parse_date("1:56 pm on 8 May, 2023") == datetime(2023, 5, 8, 13, 56, tzinfo=timezone.utc)
    assert longmemeval.parse_date("2023/05/20 (Sat) 02:21") == datetime(2023, 5, 20, 2, 21, tzinfo=timezone.utc)


def test_session_versions_are_distinguished_by_content():
    a = longmemeval.context_id("s1", "2023/05/20 (Sat) 02:21", [{"role": "user", "content": "hi"}])
    b = longmemeval.context_id("s1", "2023/05/20 (Sat) 02:21", [{"role": "user", "content": "hello"}])
    assert a != b and a.startswith("lme:s1:")


@pytest.mark.skipif(not locomo.PATH.exists(), reason="LoCoMo not downloaded (scripts/fetch_datasets.py)")
def test_locomo_split_and_categories():
    dev, held = locomo.load("dev"), locomo.load("heldout")
    assert [s["sample_id"] for s in dev] == ["conv-26", "conv-30"] and len(held) == 8
    assert {qa["category"] for s in dev for qa in s["qa"]} <= set(locomo.CATEGORIES)


@pytest.mark.skipif(not longmemeval.PATH.exists(), reason="LongMemEval not downloaded (scripts/fetch_datasets.py)")
def test_longmemeval_split():
    assert len(longmemeval.load("dev")) == 53 and len(longmemeval.load("heldout")) == 447
