"""D1 and D2 regression tests (docs/formation/rules-v2.1.md; Phase 7A pipeline-audit.md).

Each behaviour is checked for `rules:v2.1`. Where `rules:v2` shows the original defect, the same check runs
against it as a strict expected failure: `rules:v2` is kept unchanged for reproducing earlier results, and
these cases prove it still behaves as it did.
"""

from datetime import datetime, timezone

import pytest

from gupi.formation import extractors
from gupi.formation.rules_v21 import NO_AUTHOR, UNRESOLVED, UNSUPPORTED, reason_kind

SAID = datetime(2025, 8, 20, 9, tzinfo=timezone.utc)
V2_HAS_DEFECT = pytest.mark.xfail(strict=True, reason="the original defect, kept in rules:v2 for reproducibility")


def obs(text, author="p:author"):
    from gupi.records import Observation
    return Observation("src:t", "k", text, SAID, "ctx:t", author)


def run(version, text, author="p:author"):
    cset, report = extractors.get(version).extract(obs(text, author))
    return cset.candidates, report.rejected


def versions(*defective):
    """rules:v2.1 always; rules:v2 as a strict expected failure for the cases it gets wrong."""
    return [pytest.param("rules:v2.1", id="v2.1")] + [pytest.param("rules:v2", id="v2", marks=V2_HAS_DEFECT)] * bool(defective)


# --- D1: pronouns are not names ------------------------------------------------------------------------

PRONOUN_SENTENCES = [
    "She works at Acme Labs.",
    "He joined Acme in May 2025.",
    "It works for Acme.",
    "We joined Acme in 2024.",
    "Great news! She joined Acme in May 2025.",          # after sentence punctuation
    "Nora Vance is great. She joined Halden in March 2025.",  # an earlier name does not justify resolving
    "Nora Vance reports to Him.",                        # a pronoun in another role
    "She told me that Nora Vance works at Halden.",      # a pronoun as the asserter
]


@pytest.mark.parametrize("text", PRONOUN_SENTENCES)
@pytest.mark.parametrize("version", versions("defective"))
def test_d1_capitalised_pronouns_never_become_people(version, text):
    candidates, rejected = run(version, text)
    pronouns = {"She", "He", "It", "We", "They", "Him"}
    assert not [c for c in candidates if {p.surface for p in c.participants} & pronouns
                or c.attribution.asserted_by in pronouns]
    assert any(reason_kind(r) == "unresolved-reference" for _, r in rejected)


@pytest.mark.parametrize("text", ["They work at Acme.", "They joined Acme in 2024."])
def test_d1_they_is_rejected_and_reported(text):
    candidates, rejected = run("rules:v2.1", text)
    assert not candidates and rejected  # "They work" never matched; "They joined" did in rules:v2


@pytest.mark.parametrize("text", ["She told me she loves painting.", "He said the weather was lovely."])
def test_d1_a_pronoun_speaker_alone_is_not_reported_as_unresolved(text):
    # nothing in the domain would be extracted, so there is no reference to resolve
    assert all(reason_kind(r) != "unresolved-reference" for _, r in run("rules:v2.1", text)[1])


def test_d1_first_person_needs_a_known_author():
    candidates, _ = run("rules:v2.1", "I joined Acme in 2024.")
    assert [p.surface for p in candidates[0].participants if p.role == "employee"] == ["I"]   # the author
    candidates, rejected = run("rules:v2.1", "I joined Acme in 2024.", author=None)
    assert not candidates and [r for _, r in rejected] and all(r.startswith(NO_AUTHOR) for _, r in rejected)


@pytest.mark.parametrize("text, who", [
    ("Nora Vance joined Halden in March 2025.", "Nora Vance"),
    ("Shea Brandt works at Acme Labs.", "Shea Brandt"),     # starts with "She"
    ("Heidi Lee reports to Wei Chen.", "Heidi Lee"),
    ("Theo joined Acme in 2024.", "Theo"),
    ("He Wei joined Acme in 2024.", "He Wei"),              # a real surname, as a two-word name
])
def test_d1_legitimate_names_still_work(text, who):
    candidates, _ = run("rules:v2.1", text)
    assert [p.surface for c in candidates for p in c.participants][0] == who


# --- D2: unsupported employment expressions are reported ---------------------------------------------

UNSUPPORTED_SENTENCES = [
    "Nora Vance began working for Halden in March 2025.",
    "Nora Vance took a job at Halden in March 2025.",
    "Nora Vance quit Halden in May 2025.",
    "Nora Vance quit her job in May.",
    "Nora Vance resigned from Halden in May 2025.",
    "Nora Vance was appointed CTO of Halden in March 2025.",
    "Nora Vance is employed by Halden.",
    "Nora Vance was let go by Halden in May 2025.",
    "Nora Vance is Ivo Marsh's boss.",
    "Last spring I lost my job.",                            # invented forms of the Phase 7A sample's phrasings
    "I got a summer job at the harbour.",
    "I was accepted for a design placement last week.",
]
SILENT_IN_V2 = {UNSUPPORTED_SENTENCES[i] for i in (1, 2, 3, 4, 5, 6, 7, 8, 10, 11)}


@pytest.mark.parametrize("text", UNSUPPORTED_SENTENCES)
def test_d2_unsupported_expressions_are_reported_not_extracted(text):
    candidates, rejected = run("rules:v2.1", text)
    assert not candidates  # no new patterns in this milestone
    assert [reason_kind(r) for _, r in rejected] == ["unsupported-expression"]
    assert rejected[0][1].startswith(UNSUPPORTED)


@pytest.mark.parametrize("text", sorted(SILENT_IN_V2))
@pytest.mark.parametrize("version", [pytest.param("rules:v2", id="v2", marks=V2_HAS_DEFECT)])
def test_d2_rules_v2_drops_them_silently(version, text):
    assert run(version, text)[1]


@pytest.mark.parametrize("text", [
    "It began to rain.", "I took a walk after lunch.", "Dana quit smoking last year.",
    "We met at the appointed time.", "He resigned himself to waiting.", "They took the bus home.",
    "Ivo let go of the rope.", "The boss fight in the game was hard.",
])
def test_d2_unrelated_uses_are_neither_extracted_nor_reported(text):
    assert run("rules:v2.1", text) == ((), [])


@pytest.mark.parametrize("text", [
    "Nora Vance joined Halden in March 2025.", "Nora Vance started at Halden in March 2025.",
    "Nora Vance left Halden in May 2025.", "Ivo Marsh reports to Nora Vance.",
    "Nora Vance has worked at Halden since March 2025.", "Nora Vance no longer works at Halden.",
])
def test_recognised_expressions_are_unchanged(text):
    a, b = (extractors.get(v).extract(obs(text))[0].candidates for v in ("rules:v2", "rules:v2.1"))
    assert a and a == b


# --- kinds of outcome are kept apart ------------------------------------------------------------------

def test_reason_kinds_are_distinct():
    from gupi.extraction.contract import SchemaInfo
    no_reporting = SchemaInfo(frozenset({"person", "organization"}),
                              {"employment": {"employee": frozenset({"person"}), "employer": frozenset({"organization"})}},
                              {"employment": frozenset({"job-title"})})
    _, report = extractors.get("rules:v2.1").extract(obs("Ivo Marsh reports to Nora Vance."), schema=no_reporting)
    kinds = {reason_kind(r) for _, r in report.rejected}
    assert kinds == {"validation"}
    assert reason_kind(run("rules:v2.1", "Nora Vance works hard at the weekend.")[1][0][1]) == "no-pattern"
    assert reason_kind(UNRESOLVED) == "unresolved-reference" and reason_kind(NO_AUTHOR) == "no-author"
    assert run("rules:v2.1", "") == ((), [])          # empty input: nothing, and nothing to report
    assert run("rules:v2.1", "   \n ") == ((), [])


def test_versions_are_selectable_and_named():
    assert extractors.get("rules:v2").method == "rules:v2"
    assert extractors.get("rules:v2.1").method == "rules:v2.1"
    assert set(extractors.VERSIONS) == {"rules:v2", "rules:v2.1"}
    with pytest.raises(KeyError):
        extractors.get("rules:v3")


# --- the frozen sets: candidates and formation decisions are unchanged where no pronoun is involved ----

def test_frozen_6b_set_candidates_and_decisions_are_identical():
    from gupi.formation import evaluation
    from gupi.formation.form import decide
    data = evaluation.load()
    a, b = (evaluation.run(extractors.get(v), data) for v in ("rules:v2", "rules:v2.1"))
    for pid in a:
        assert a[pid].candidates == b[pid].candidates, pid
        assert [decide(c, [], {}) for c in a[pid].candidates] == [decide(c, [], {}) for c in b[pid].candidates]


@pytest.mark.parametrize("split", ["heldout", "dev"])
def test_phase2_conversations_are_identical(split):
    from gupi.formation import evaluation
    got = {v: evaluation.score_conversations(split, evaluation.rules_v2_claims(extractors.get(v)))
           for v in ("rules:v2", "rules:v2.1")}
    assert got["rules:v2"] == got["rules:v2.1"]
