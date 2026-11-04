"""The Stage 3 scorer with real formation (a disposable local TypeDB database), on the synthetic fixtures:
corrections are reviewed, a forwarded copy is withheld, nothing is superseded, and no severe error occurs."""

import sys
from pathlib import Path

import pytest

from gupi.benchmarks.phase7b import stage3

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "fixtures"))
import stage3_synthetic as syn  # noqa: E402

pytestmark = pytest.mark.integration


def test_formation_outcomes_on_the_synthetic_fixtures(tmp_path, driver):
    pub, priv, resp = syn.write(tmp_path)
    r = stage3.run(pub, priv, resp, with_formation=True, driver=driver)
    m, rules = r["systems"][stage3.MODEL_METHOD], r["systems"]["rules:v2.1"]
    assert r["typedb"] == "3.14.1" and r["responses"]["missing"] == [] and r["responses"]["unexpected"] == []
    assert m["pipeline"]["formation"] == {"formed": 6, "review": 2, "withheld": 1, "rejected": 0}
    assert m["pipeline"]["supersessions_during_run"] == 0 and m["pipeline"]["duplicate_original_attestations"] == 0
    assert m["pipeline"]["formation_failures"] == [] and m["pipeline"]["validator_rejections"] == {"extractor": 0, "store": 0}
    assert m["severe_errors"]["count"] == 0
    assert m["integrity"]["independent_corroboration"]["k"] == m["integrity"]["independent_corroboration"]["n"] == 9
    assert m["summary"]["formation_agrees_with_expected_admission"]["k"] == 9
    assert rules["pipeline"]["supersessions_during_run"] == 0          # the baseline runs on the same inputs
