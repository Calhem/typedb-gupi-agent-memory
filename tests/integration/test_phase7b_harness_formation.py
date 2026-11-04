"""The offline harness with formation (local TypeDB only) on the developer fixtures: the outcomes the
fixtures were written to produce."""

import pytest

from gupi.benchmarks.phase7b import harness

pytestmark = pytest.mark.integration
FIX = harness.Path(__file__).resolve().parents[1] / "fixtures" / "phase7b-dev" / "offline"


def test_formation_outcomes_on_the_developer_fixtures(driver):
    r = harness.run(FIX, responses=FIX / "responses.json", with_formation=True, driver=driver)
    m, rules = r["systems"][harness.MODEL_METHOD]["summary"], r["systems"]["rules:v2.1"]["summary"]
    assert r["typedb"] == "3.14.1"
    # Stage 2B: F1 fixed, so DEV-108 (a second forwarded copy of Dana Okoro's statement) is withheld;
    # C2: DEV-105's organisational claimant (Halden Press) now gives a candidate, sent to review as an allegation;
    # D3: DEV-126's retraction with no matchable target now gives a null-target candidate, sent to review
    assert m["formation"] == {"formed": 11, "review": 6, "withheld": 2} and rules["formation"] == {"formed": 11, "review": 2, "withheld": 1}
    assert m["severe_errors"]["count"] == rules["severe_errors"]["count"] == 0
    assert m["counts"]["copies_formed"] == rules["counts"]["copies_formed"] == 0
    outcomes = {p["passage"]: sorted(o["kind"] for o in p["outcomes"]) for p in r["systems"][harness.MODEL_METHOD]["passages"]}
    assert outcomes["DEV-115"] == outcomes["DEV-122"] == ["invalid-model-output"]
    assert outcomes["DEV-117"] == outcomes["DEV-119"] == ["grounding-failure"]
    assert outcomes["DEV-105"] == outcomes["DEV-126"] == []
    status = {p["passage"]: [c["status"] for c in p["candidates"]] for p in r["systems"][harness.MODEL_METHOD]["passages"]}
    flags = {p["passage"]: sorted(f["kind"] for f in p["flags"]) for p in r["systems"][harness.MODEL_METHOD]["passages"]}
    assert status["DEV-105"] == status["DEV-126"] == ["review"] and status["DEV-108"] == ["withheld"]
    assert "correction-target-unresolved" in flags["DEV-126"] and "allegation" in flags["DEV-105"]
