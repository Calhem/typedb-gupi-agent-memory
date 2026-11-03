"""The retrieval benchmark runner works end to end. Scores are reported in docs, not pinned in tests, so
nothing is tuned against the frozen benchmark."""

import pytest

from gupi.retrieval_eval import run

pytestmark = pytest.mark.integration


def test_runner_scores_every_question_for_both_systems(driver):
    result = run("gold", driver)
    for system in ("structured", "keyword"):
        assert len(result[system]["rows"]) == 15 and result[system]["questions"] == 15
