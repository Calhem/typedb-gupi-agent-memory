"""The rule extractor on the development conversations, end to end through TypeDB (a regression guard).

Held-out conversations are deliberately not used in tests, so nothing is tuned against them.
"""

import pytest

from gupi.evaluation import load, score
from gupi.extraction.rules import RuleExtractor

pytestmark = pytest.mark.integration


def test_rule_extractor_on_development_set(driver):
    report = score(load("dev"), RuleExtractor(), driver)
    assert report["claims"]["precision"] == 1.0 and report["claims"]["tp"] == 11 and report["claims"]["gold"] == 12
    assert report["time_correct_of_matched"] == {"correct": 11, "matched": 11}
    assert report["errors"] == {"missed: nothing extracted from the message": 1}  # the pronoun "He"
    assert report["basis"] == {"explicit": 11}
