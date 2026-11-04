"""The offline harness with formation (local TypeDB only) on the developer fixtures: the outcomes the
fixtures were written to produce."""

import pytest

from gupi.benchmarks.phase7b import harness

pytestmark = pytest.mark.integration
FIX = harness.Path(__file__).resolve().parents[1] / "fixtures" / "phase7b-dev" / "offline"


def test_formation_outcomes_on_the_developer_fixtures(driver):
    r = harness.run(FIX, responses=FIX / "responses.json", with_formation=True, driver=driver)
    m, rules = r["systems"]["model:candidate-v1"]["summary"], r["systems"]["rules:v2.1"]["summary"]
    assert r["typedb"] == "3.14.1"
    assert m["formation"] == {"formed": 12, "review": 4, "withheld": 1} and rules["formation"] == {"formed": 12, "review": 2}
    assert m["severe_errors"]["count"] == rules["severe_errors"]["count"] == 0
    assert m["counts"]["copies_formed"] == rules["counts"]["copies_formed"] == 1    # finding F1 (DEV-108)
    outcomes = {p["passage"]: sorted(o["kind"] for o in p["outcomes"]) for p in r["systems"]["model:candidate-v1"]["passages"]}
    assert outcomes["DEV-115"] == outcomes["DEV-122"] == ["invalid-model-output"]
    assert outcomes["DEV-117"] == outcomes["DEV-119"] == ["grounding-failure"]
    assert outcomes["DEV-105"] == ["claimant-kind-not-representable"] and outcomes["DEV-126"] == ["correction-target-unresolved"]
