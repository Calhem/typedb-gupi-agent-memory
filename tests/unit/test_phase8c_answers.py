"""The answer-level harness, offline: a stand-in protocol file and scripted replies. No model, no AML text."""

import hashlib
import json

import pytest

from gupi.benchmarks import phase8c_answers as a
from gupi.budget import BudgetExceeded
from gupi.formation.chat_extractor import Recording, RunStopped

TEMPLATE = "M1 {{speaker_1_name}}: {{speaker_1_memories}}\nM2 {{speaker_2_name}}: {{speaker_2_memories}}\nQ: {{question}}"
JUDGE = 'Q {question} G {gold_answer} A {generated_answer} {{"label": "x"}}'


def text(reply):
    return {"model": "gpt-4o-mini-2024-07-18", "choices": [{"finish_reason": "stop", "message": {"content": reply}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 10}}


class FakeLedger:
    def __init__(self, refuse=False):
        self.settled, self.failed, self.refuse = [], [], refuse

    def reserve(self, *a, **k):
        if self.refuse:
            raise BudgetExceeded("over")
        return "c", 1

    def settle(self, call, attempts):
        self.settled.append(attempts)

    def fail(self, call):
        self.failed.append(call)


def test_the_protocol_is_read_as_data_and_never_run(tmp_path):
    f = tmp_path / "pipeline.py"
    source = f'raise SystemExit("executed")\nOPEN_ENDED_ANSWER_TEMPLATE = {TEMPLATE!r}\nACCURACY_PROMPT = {JUDGE!r}\n'
    f.write_text(source)
    assert a.load_protocol(f, hashlib.sha256(source.encode()).hexdigest()) == (TEMPLATE, JUDGE)
    with pytest.raises(ValueError):
        a.load_protocol(f, "0" * 64)


def test_the_repository_holds_no_copy_of_the_protocol():
    import inspect
    assert "Inclusion + Non-contradiction" not in inspect.getsource(a)


def test_only_the_notes_differ_between_plain_and_qualified():
    items = [("2023-05-08", "Juno", "Bram left.", ("unresolved: identity not confirmed",))]
    assert a.memories(items, False) == "[2023-05-08] Juno: Bram left."
    assert a.memories(items, True) == "[2023-05-08] Juno: Bram left. (unresolved: identity not confirmed)"


def test_conditions_share_one_budget_and_differ_only_as_intended():
    items = [("2023-05-08", "Juno", "Bram left in May.", ("sources disagree on the date",)), ("2023-05-09", "Juno", "x" * 40, ())]
    facts = [("Bram left Fenwick Labs.", ("sources disagree on the date",))]
    raw = a.condition_block(items, facts, "raw", 500)
    claims = a.condition_block(items, facts, "raw+claims", 500)
    full = a.condition_block(items, facts, "raw+claims+qualifications", 500)
    assert "Fact:" not in raw and "disagree" not in raw
    assert "Fact: Bram left Fenwick Labs." in claims and "disagree" not in claims
    assert full.count("sources disagree") == 2
    tight = 90
    assert all(len(a.condition_block(items, facts, c, tight)) <= tight for c in a.CONDITIONS)
    assert "x" * 40 not in a.condition_block(items, facts, "raw+claims", tight)      # structure displaces raw text
    with pytest.raises(ValueError):
        a.condition_block(items, facts, "other", 10)


def test_prompts_fill_every_field():
    out = a.answer_prompt(TEMPLATE, "Why?", (("A", "m1"), ("B", "m2")))
    assert "{{" not in out and "A: m1" in out and "Q: Why?" in out
    assert "G gold A gen" in a.judge_prompt(JUDGE, "q", "gold", "gen")


@pytest.mark.parametrize("reply, label", [('Fine. {"label": "CORRECT"}', "CORRECT"), ('```json\n{"label": "wrong"}\n```', "WRONG"),
                                          ("no json", None), ('{"label": "MAYBE"}', None), (None, None), ("{broken}", None)])
def test_judge_labels_are_read_strictly(reply, label):
    assert a.judge_label(reply) == label


def attribute(label="WRONG", answer="Oslo", gold=("g",), shown=(), depth=(), statuses=None, context="", claims=True):
    return a.attribute(label, answer, gold, shown, depth, statuses or {}, context, claims)


@pytest.mark.parametrize("kwargs, verdict", [
    (dict(label="CORRECT", shown=("g",)), "correct"),
    (dict(label="CORRECT"), "unsupported"),
    (dict(shown=("g",)), "answer-generation"),
    (dict(depth=("g",)), "ranking"),
    (dict(statuses={}), "extraction"),
    (dict(statuses={"g": {"review"}}), "formation-or-review"),
    (dict(statuses={"g": {"withheld", "rejected"}}), "formation-or-review"),
    (dict(statuses={"g": {"formed"}}), "retrieval"),
    (dict(claims=False), "retrieval"),
    (dict(answer="In 2019", shown=("g",), context="2021"), "temporally-invalid"),
    (dict(answer="In May", shown=("g",), context="[2021] in May"), "answer-generation"),
])
def test_each_failure_is_attributed_to_its_first_cause(kwargs, verdict):
    assert attribute(**kwargs) == verdict and verdict in a.VERDICTS


def client(tmp_path, *replies, ledger=None, max_calls=9):
    left = list(replies)

    def transport(body):
        return left.pop(0)
    return a.AnswerClient(Recording(tmp_path / "a.jsonl"), transport, ledger or FakeLedger(), max_calls)


PEOPLE = (("Juno", [("2023-05-08", "Juno", "We met in Oslo.", ())]), ("Bram", []))


def score(c, **over):
    return a.score_question(c, (TEMPLATE, JUDGE), "Where?", "Oslo", PEOPLE, ["g"], ["g"], ["g"], {}, **over)


def test_a_question_end_to_end_and_its_replay(tmp_path):
    ledger = FakeLedger()
    c = client(tmp_path, text("Oslo"), text('{"label": "CORRECT"}'), ledger=ledger)
    assert score(c) == {"answer": "Oslo", "label": "CORRECT", "verdict": "correct"}
    assert len(ledger.settled) == 2
    replay = a.AnswerClient(Recording(tmp_path / "a.jsonl"))
    assert score(replay)["verdict"] == "correct" and replay.calls == 0


def test_failed_generation_or_judgement_is_unjudged_never_wrong(tmp_path):
    assert score(client(tmp_path, {"error": {"reason": "down"}}))["verdict"] == "unjudged"
    (tmp_path / "a.jsonl").unlink()
    assert score(client(tmp_path, text("Oslo"), text("no label")))["verdict"] == "unjudged"
    (tmp_path / "a.jsonl").unlink()
    assert score(a.AnswerClient(Recording(tmp_path / "a.jsonl")))["verdict"] == "unjudged"


def test_paid_calls_are_budgeted_limited_and_off_by_default(tmp_path):
    with pytest.raises(ValueError):
        a.AnswerClient(Recording(tmp_path / "a.jsonl"), transport=lambda b: {})
    with pytest.raises(RunStopped):
        score(client(tmp_path, text("x"), max_calls=0))
    with pytest.raises(RunStopped):
        score(client(tmp_path, text("x"), ledger=FakeLedger(refuse=True)))


def test_the_estimate_is_a_small_stated_figure():
    e = a.estimate(135)
    assert e["answers"] == e["judgements"] == 675 and 0.1 < e["usd"] < 1.0
    assert json.dumps(e)
