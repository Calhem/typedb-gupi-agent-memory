"""rules:v2, the offline candidate extractor (Phase 6B). Sentences here are the tests' own; the frozen evaluation
set (tests/fixtures/formation/eval-v1.json) is used only by the evaluation."""

from datetime import datetime, timezone

from gupi.extraction.contract import SchemaInfo
from gupi.formation.candidate import from_dict, to_dict
from gupi.formation.rules_v2 import RulesV2
from gupi.formation.validate import valid_time, validate
from gupi.records import Observation
from gupi.temporal import ValidTime

SAID = datetime(2025, 8, 20, 9, tzinfo=timezone.utc)


def d(y, m=1, day=1):
    return datetime(y, m, day, tzinfo=timezone.utc)


def extract(text, author=None, prior=(), schema=None):
    obs = Observation("src:t", "k", text, SAID, author_id=author)
    cset, report = RulesV2().extract(obs, prior=prior, schema=schema)
    assert validate(cset, obs, schema) == []   # everything emitted is structurally valid
    return cset, report


def only(text, **kw):
    cset, _ = extract(text, **kw)
    (c,) = cset.candidates
    return c


def kinds(c):
    return {t.kind: t for t in c.times}


# --- exact starts against lower-bound continuity ------------------------------------------------------

def test_joined_in_march_is_a_start():
    c = only("Lina Hart joined Corbel in March 2025.")
    t = kinds(c)["start"]
    assert (c.claim_type, t.phrase, t.earliest, t.latest, t.precision) == ("employment", "March 2025", d(2025, 3), d(2025, 4), "month")
    assert valid_time(c)[0] == ValidTime(d(2025, 3), d(2025, 4))


def test_since_march_is_lower_bound_continuity_keeping_the_possible_march_interval():
    for text in ("Lina Hart has worked at Corbel since March 2025.", "Since March 2025, Lina Hart works at Corbel."):
        c = only(text)
        k = kinds(c)
        assert "start" not in k and (k["holds-since"].earliest, k["holds-since"].latest) == (d(2025, 3), d(2025, 4))
        assert k["holds-at"].earliest == SAID
        assert valid_time(c) == (ValidTime(None, d(2025, 4), SAID), "ongoing-at-observation")  # certain from 1 April
    c = only("Lina Hart has reported to Sam Ode since March 2025.")
    assert c.claim_type == "reporting" and "holds-since" in kinds(c) and "start" not in kinds(c)


# --- plans, uncertainty and hedges ----------------------------------------------------------------------

def test_plans_hedges_and_uncertainty_are_kept_apart_from_extractor_confidence():
    cases = {
        "Lina Hart will join Corbel in October 2025.": ("planned", "certain"),
        "Lina Hart might join Corbel in October 2025.": ("planned", "possible"),
        "Lina Hart is leaving Corbel in October 2025.": ("planned", "certain"),
        "I think Lina Hart reports to Sam Ode.": ("actual", "probable"),
        "Lina Hart probably still works at Corbel.": ("actual", "probable"),
    }
    for text, (modality, commitment) in cases.items():
        c = only(text)
        assert (c.modality, c.commitment, c.confidence) == (modality, commitment, None), text
    rumour = only("Reportedly, Lina Hart left Corbel in July 2025.")
    assert (rumour.attribution.mode, rumour.commitment) == ("rumour", "unknown")
    planned = only("Lina Hart will join Corbel in October 2025.")
    assert kinds(planned)["start"].earliest == d(2025, 10)  # read as future, from "will"


# --- explicit negation ----------------------------------------------------------------------------------

def test_explicit_negation_is_polarity_at_its_own_time_not_an_end_date():
    for text in ("Lina Hart no longer works at Corbel.", "Lina Hart isn't with Corbel any more.",
                 "Lina Hart doesn't report to Sam Ode."):
        c = only(text)
        assert c.polarity == "negative" and set(kinds(c)) == {"holds-at"}, text   # no end is invented
        assert kinds(c)["holds-at"].earliest == SAID


# --- corrections ----------------------------------------------------------------------------------------

def test_a_stated_correction_names_the_candidate_it_corrects_and_changes_nothing():
    first, _ = extract("Lina Hart joined Corbel in March 2025.")
    fix = only("Correction: Lina Hart joined Corbel in April 2025, not March.", prior=(first,))
    (r,) = fix.relations
    assert (r.kind, r.target, r.marked, r.cue) == ("corrects", first.candidates[0].id, "stated", "Correction:")
    assert kinds(fix)["start"].earliest == d(2025, 4)
    assert kinds(first.candidates[0])["start"].earliest == d(2025, 3)  # the earlier candidate is untouched


def test_a_correction_without_an_earlier_candidate_records_no_relation_and_says_so():
    cset, report = extract("Correction: Lina Hart joined Corbel in April 2025, not March.")
    assert cset.candidates[0].relations == ()
    assert any("no earlier candidate" in n for n in report.notes)


# --- speaker attribution against document authorship ----------------------------------------------------

def test_reported_speech_is_attributed_to_the_speaker_not_the_author():
    c = only("Ravi told me that Lina Hart left Corbel in May 2025.", author="p:wen")
    assert (c.attribution.asserted_by, c.attribution.mode, c.attribution.via) == ("Ravi", "reported", ("p:wen",))
    own = only("Lina Hart left Corbel in May 2025.", author="p:wen")
    assert (own.attribution.asserted_by, own.attribution.mode, own.attribution.via) == (None, "direct", ())
    me = only("I joined Corbel in May 2024.", author="p:wen")
    assert me.participants[0].surface == "I" and me.attribution.asserted_by is None  # "I" is the author
    cset, _ = extract("I joined Corbel in May 2024.")
    assert cset.candidates == ()  # first person with no known author: not extracted


# --- forwarded statements and non-independent corroboration ---------------------------------------------

def test_a_forwarded_copy_repeats_the_original_and_is_not_independent():
    text = ("Lina Hart has reported to Sam Ode since April 2025.\n---- Forwarded message ----\n"
            "From: Sam Ode\nLina Hart has reported to Sam Ode since April 2025.")
    cset, _ = extract(text)
    own, fwd = cset.candidates
    assert own.attribution.mode == "direct" and own.relations == ()
    assert (fwd.attribution.mode, fwd.attribution.asserted_by, fwd.attribution.transmission) == \
        ("forwarded", "Sam Ode", ("forwarded",))
    assert [(r.kind, r.target) for r in fwd.relations] == [("repeats", own.id)]
    independent = [c for c in cset.candidates if not any(r.kind == "repeats" for r in c.relations)]
    assert len(independent) == 1


# --- temporal ambiguity and source preservation ---------------------------------------------------------

def test_ambiguous_or_unreadable_time_is_kept_as_written():
    c = only("Lina Hart stopped reporting to Sam Ode in May.")
    t = kinds(c)["end"]
    assert (t.phrase, t.earliest, t.explicit) == ("May", d(2025, 5), False) and t.assumption
    text = "Since last spring, Lina Hart has been reporting to Sam Ode."
    c = only(text)
    t = kinds(c)["holds-since"]
    assert (t.phrase, t.earliest, t.latest, t.precision) == ("last spring", None, None, "unknown")
    assert c.passage.text == text and text[t.start:t.end] == "last spring"
    assert valid_time(c)[0] == ValidTime(to_earliest=SAID)  # the unread phrase adds no bound


def test_two_clauses_give_two_candidates_with_the_shared_passage():
    text = "Lina Hart has been at Corbel since 2024 and reports to Sam Ode."
    emp, rep = only_two(text)
    assert (emp.claim_type, rep.claim_type) == ("employment", "reporting")
    assert emp.passage == rep.passage and rep.participants[0].surface == "Lina Hart"


def only_two(text):
    cset, _ = extract(text)
    assert len(cset.candidates) == 2
    return cset.candidates


# --- idempotency, stable ids, rejection ------------------------------------------------------------------

def test_extraction_is_deterministic_with_stable_ids():
    text = "Lina Hart joined Corbel in March 2025. Ravi said Lina Hart reports to Sam Ode."
    a, _ = extract(text, author="p:wen")
    b, _ = extract(text, author="p:wen")
    assert a == b and [c.id for c in a.candidates] == [c.id for c in b.candidates] and len(a.candidates) == 2
    assert from_dict(to_dict(a)) == a


def test_unsupported_and_malformed_input_is_rejected_not_guessed():
    cset, report = extract("Corbel is hiring. The office is cold.")
    assert cset.candidates == () and report.rejected == []          # nothing in the domain: nothing to report
    cset, report = extract("Lina Hart joined.")
    assert cset.candidates == () and "no supported pattern" in report.rejected[0][1]
    c = only("Lina Hart joined Corbel in Smarch 2025.")
    assert kinds(c)["start"].precision == "unknown"                  # kept as written, no invented date
    no_reporting = SchemaInfo(frozenset({"person", "organization"}),
                              {"employment": {"employee": frozenset({"person"}), "employer": frozenset({"organization"})}},
                              {"employment": frozenset({"job-title"})})
    cset, report = RulesV2().extract(Observation("src:t", "k", "Lina Hart reports to Sam Ode.", SAID), schema=no_reporting)
    assert cset.candidates == () and "not available" in report.rejected[0][1]
