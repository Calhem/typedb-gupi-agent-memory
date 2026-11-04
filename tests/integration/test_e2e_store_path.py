"""Phase 6D runner, live: the adversarial path really goes through the candidate store, in its own database."""

import json

import pytest

from gupi.benchmarks.e2e import adversarial

pytestmark = pytest.mark.integration


def test_adversarial_case_goes_through_the_store(driver):
    case = json.loads(adversarial.frozen.DATA.read_text())["cases"][0]
    before = {d.name for d in driver.databases.all()}
    got = adversarial.run_case(driver, case)
    assert got["store_used"] and got["claims_without_store_link"] == 0
    assert got["candidate_outcomes"] == [("m1", "formed")]
    assert adversarial.frozen.score(case, got) == ({m: True for m in adversarial.frozen.MEASURES}, False)
    assert {d.name for d in driver.databases.all()} == before  # its own database was deleted afterwards
