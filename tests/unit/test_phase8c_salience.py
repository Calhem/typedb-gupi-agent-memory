"""The exploratory ordering and the cost table: no database and no dataset."""

from gupi.benchmarks import phase8c_coverage as coverage
from gupi.benchmarks import phase8c_manual as manual
from gupi.benchmarks import phase8c_salience as s


def test_promotion_reorders_and_removes_nothing():
    out = s.promote(["a", "b", "c", "d", "e"], {"e"}, 1)
    assert out[0] == "a" and sorted(out) == list("abcde") and out.index("e") < 4


def test_adding_brings_in_turns_the_words_missed_without_moving_the_top():
    out = s.add_all(["a", "b"], {"z"}, 1)
    assert out[0] == "a" and set(out) == {"a", "b", "z"}


def test_the_filter_keeps_statements_and_skips_chatter():
    assert s.worth_reading("I went to Oslo last week.")
    assert s.worth_reading("Thanks! My kids started school yesterday.")
    assert not s.worth_reading("Wow, that's great!")
    assert not s.worth_reading("Did you go to Oslo?")
    assert not s.worth_reading("Nice! [shared image: I went to a park yesterday]")


def test_the_cost_table_falls_with_batching_and_filtering():
    rows = s.scale_table()["rows"]
    every, batched, filtered = rows["every turn, 1 per request"], rows["every turn, 20 per request"], rows["text filter, 20 per request"]
    assert round(every["calls"] / batched["calls"]) == 20
    assert every["usd"] > batched["usd"] > filtered["usd"] > 0


def test_stop_causes_are_named_from_the_words():
    assert manual.cause({"p": [["subject", "my kids", "person", True]], "e": "my kids"}, "") == ": my or our"
    assert manual.cause({"p": [["subject", "We", "person", True]], "e": "We"}, "") == ": we"
    assert manual.cause({"p": [["subject", "she", "person", True]], "e": "she"}, "") == ": another pronoun or vague phrase"
    assert manual.cause({"p": [["subject", "I", "person"]], "e": "Went to Oslo"}, "") == ": no stated subject"
    assert manual.cause({"p": [["subject", "I", "person"]], "e": "I went"}, "") == ""


def outcome(label):
    case = next(c for c in coverage.CASES if c[1] == label)
    return coverage.probe(*case)["result"]


def test_what_the_parser_fix_recovered_is_recorded():
    assert outcome("capital I inside a word") == "formed"
    assert outcome("two I in the smallest span") == "formed"


def test_protections_hold_on_every_probe():
    assert outcome("hedge") == "review"
    assert outcome("a plan") == "cue-conflict" and outcome("negation") == "cue-conflict"
    assert outcome("pronoun for a named person") == "ambiguous-reference"
    assert outcome("inferred, declared") == "inferred-not-admissible"


def test_known_exclusions_stay_visible_until_someone_decides_otherwise():
    """Each of these is a proposal awaiting the owner. If one changes, the coverage analysis must change with it."""
    assert outcome("bare relation") == "ambiguous-reference"
    assert outcome("relation with a name, the kinship") == "grounding-failure"
    assert outcome("exact day") == "withheld" and outcome("relative week") == "withheld"
    assert outcome("no subject") == "grounding-failure"
