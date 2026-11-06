"""Phase 8C.4: does retrieved evidence let a model answer correctly, and if not, where did it break?

    uv run python -I -m gupi.benchmarks.phase8c_answers plan --questions N
    (`score_question` is complete and tested offline; a paid run has no command until it has its own approval)

The answer and judge prompts follow AML's published LoCoMo-Refined pipeline at a pinned commit. That repository has no
licence, so its prompts are not copied here: `load_protocol` reads them from a copy in git-ignored `.data/`, as text,
checks its hash, and never runs it. AML does not publish its answer or judge models, so `gpt-4o-mini` stands in for
both; these are not AML scores.
"""

import argparse
import ast
import hashlib
import json
import re
from pathlib import Path

from gupi.benchmarks import common
from gupi.budget import Attempt, BudgetExceeded
from gupi.formation.chat_extractor import RunStopped, outcome, request_key

MODEL = "gpt-4o-mini"
PROTOCOL_COMMIT = "f4f82ffb235ab52e5b521839b139bfd858be7ee6"
PROTOCOL_SHA256 = "31a49fc09e381bc117b59063c7a4cea543a672b23e1264aedb03290239671c1a"
PROTOCOL_PATH = common.ROOT / ".data" / "aml-pipeline" / PROTOCOL_COMMIT / "locomo-refined-pipeline.py"
MAX_OUTPUT = 256
VERDICTS = ("correct", "extraction", "formation-or-review", "retrieval", "ranking", "answer-generation", "unsupported",
            "temporally-invalid", "unjudged")


def load_protocol(path=PROTOCOL_PATH, sha256=PROTOCOL_SHA256):
    """The two prompt templates, read as constants from the file's syntax tree. The file is data and is never executed."""
    source = Path(path).read_bytes()
    if hashlib.sha256(source).hexdigest() != sha256:
        raise ValueError("the protocol file differs from the pinned version")
    constants = {n.targets[0].id: n.value.value for n in ast.parse(source).body
                 if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant) and isinstance(n.targets[0], ast.Name)}
    return constants["OPEN_ENDED_ANSWER_TEMPLATE"], constants["ACCURACY_PROMPT"]


def memories(items, qualified):
    """The evidence as the answering model sees it. Same items either way, so comparing the two measures qualifications
    alone. `items`: (date, speaker, text, notes)."""
    lines = []
    for date, speaker, text, notes in items:
        tail = f" ({'; '.join(notes)})" if qualified and notes else ""
        lines.append(f"[{date}] {speaker}: {text}{tail}")
    return "\n".join(lines)


def answer_prompt(template, question, people):
    """`people`: exactly the two speakers as (name, memories), the protocol's shape."""
    (a, ma), (b, mb) = people
    values = {"speaker_1_name": a, "speaker_1_memories": ma, "speaker_2_name": b, "speaker_2_memories": mb, "question": question}
    return re.sub(r"\{\{(\w+)\}\}", lambda m: values[m.group(1)], template)


def judge_prompt(template, question, gold, generated):
    values = {"question": question, "gold_answer": gold, "generated_answer": generated}
    return re.sub(r"\{(question|gold_answer|generated_answer)\}", lambda m: values[m.group(1)], template)


def request(prompt):
    return {"model": MODEL, "temperature": 0, "max_completion_tokens": MAX_OUTPUT, "messages": [{"role": "user", "content": prompt}]}


def judge_label(text):
    found = re.findall(r"\{[^{}]*\}", text or "")
    try:
        label = str(json.loads(found[-1]).get("label", "")).upper()
    except (IndexError, ValueError):
        return None
    return label if label in ("CORRECT", "WRONG") else None


YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
MONTH = re.compile(r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\b")


def invented_date(answer, context):
    """A year or month in the answer that appears nowhere in the evidence shown: a temporal claim with no support."""
    return any(w not in context for pattern in (YEAR, MONTH) for w in pattern.findall(answer or ""))


def attribute(label, answer, gold, context_ids, depth_ids, statuses, context_text, uses_claims):
    """Where one question broke, first cause first. `statuses` maps a turn to the formation outcomes of its candidates;
    absent means no candidate was extracted from it. Only a claim system can fail at extraction or formation."""
    gold, shown = set(gold), set(context_ids)
    if label == "CORRECT":
        return "unsupported" if gold and not gold & shown else "correct"
    if invented_date(answer, context_text):
        return "temporally-invalid"
    missing = gold - shown
    if not missing:
        return "answer-generation"
    if missing <= set(depth_ids):
        return "ranking"
    if uses_claims:
        lost = missing - set(depth_ids)
        if any(g not in statuses for g in lost):
            return "extraction"
        if all("formed" not in statuses[g] for g in lost):
            return "formation-or-review"
    return "retrieval"


class AnswerClient:
    """One generation or judgement, recorded before use, reserved before sending, replayed when already recorded."""

    def __init__(self, recording, transport=None, ledger=None, max_calls=0):
        if (transport is None) != (ledger is None):
            raise ValueError("a transport without a ledger, or the reverse, is not allowed")
        self.recording, self.transport, self.ledger, self.max_calls, self.calls = recording, transport, ledger, max_calls, 0

    def complete(self, prompt, purpose):
        """The reply's text, or None with the failure recorded."""
        body = request(prompt)
        key = request_key(body)
        entry = self.recording.get(key)
        if entry is None:
            if self.transport is None:
                return None
            if self.calls >= self.max_calls:
                raise RunStopped(f"the run's limit of {self.max_calls} calls was reached")
            try:
                call, _ = self.ledger.reserve(MODEL, purpose, len(prompt.encode()) + 1000, MAX_OUTPUT, fallback_attempts=0)
            except BudgetExceeded as e:
                raise RunStopped(str(e)) from e
            self.calls += 1
            try:
                reply = self.transport(body)
            except Exception as e:
                reply = {"error": {"reason": type(e).__name__}}
            usage = reply.get("usage")
            if usage:
                model = MODEL if str(reply.get("model", "")).startswith(MODEL) else reply.get("model")
                self.ledger.settle(call, [Attempt(model, usage["prompt_tokens"], usage["completion_tokens"])])
            else:
                self.ledger.fail(call)
            entry = {"key": key, "purpose": purpose, "requested_model": MODEL, "reply": reply}
            self.recording.add(entry)
        return outcome(entry["reply"])[1]


def score_question(client, templates, question, gold_answer, people, gold_turns, context_ids, depth_ids, statuses,
                   qualified=True, uses_claims=False):
    """One question for one system. `people`: the two (name, items) pairs. Returns the answer, the judge's label and
    the first cause of any failure. A failed generation or judgement is reported as unjudged, never as wrong."""
    template, judge = templates
    shown = [(name, memories(items, qualified)) for name, items in people]
    context = "\n".join(text for _, text in shown)
    generated = client.complete(answer_prompt(template, question, shown), "phase8c-answer")
    if generated is None:
        return {"answer": None, "label": None, "verdict": "unjudged"}
    label = judge_label(client.complete(judge_prompt(judge, question, gold_answer, generated), "phase8c-judge"))
    if label is None:
        return {"answer": generated, "label": None, "verdict": "unjudged"}
    return {"answer": generated, "label": label, "verdict": attribute(label, generated, gold_turns, context_ids, depth_ids,
                                                                      statuses, context, uses_claims)}


def estimate(questions, systems=5, turns_in_context=100, chars_per_turn=160):
    """Answer plus judge for each question and system. Characters / 4 for tokens; 30 output tokens to answer, 60 to judge."""
    prompt = (turns_in_context * chars_per_turn + 1800) // 4
    calls = questions * systems
    return {"answers": calls, "judgements": calls, "usd": round(calls * (prompt * .15 + 30 * .6 + 500 * .15 + 60 * .6) / 1e6, 2)}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("command", choices=("plan",))
    p.add_argument("--questions", type=int, default=135)
    args = p.parse_args(argv)
    print(json.dumps(estimate(args.questions)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
