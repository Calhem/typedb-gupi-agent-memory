"""LongMemEval (S, cleaned) adapter: each question's history sessions -> dated contexts, turns -> observations.

Sessions are reused across questions, but 4,672 reuses of a session id differ in content or date, so a
context is one exact version of a session (id + content hash). Gold units: the answer sessions, and the
answer turns the dataset marks (`has_answer`). Data stays in .data/ (MIT; see docs/datasets.md).
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone

from gupi.benchmarks.common import ROOT, SPLIT, BenchQuestion
from gupi.records import Batch, Context, Observation, Referent, Source

PATH = ROOT / ".data" / "longmemeval" / "longmemeval_s_cleaned.json"
SOURCE = Source("src:longmemeval", "conversation", label="LongMemEval S (cleaned)")
ROLES = {"user": Referent("lme:user", "person", "user"), "assistant": Referent("lme:assistant", "unclassified", "assistant")}


def load(split):
    data = json.loads(PATH.read_text())
    dev = set(SPLIT["longmemeval_s_cleaned"]["dev"])
    return [q for q in data if (q["question_id"] in dev) == (split == "dev")]


def parse_date(text):
    return datetime.strptime(text.strip(), "%Y/%m/%d (%a) %H:%M").replace(tzinfo=timezone.utc)


def context_id(session_id, date, turns):
    digest = hashlib.sha256(json.dumps([date, [(t["role"], t["content"]) for t in turns]]).encode()).hexdigest()[:12]
    return f"lme:{session_id}:{digest}"


def ingest(memory, clock, items):
    """Ingest every distinct session version once, oldest first. Returns {context id: [observation ids]}."""
    versions = {}
    for q in items:
        for sid, date, turns in zip(q["haystack_session_ids"], q["haystack_dates"], q["haystack_sessions"]):
            versions.setdefault(context_id(sid, date, turns), (sid, date, turns))
    by_context = {}
    for cid, (sid, date, turns) in sorted(versions.items(), key=lambda kv: (parse_date(kv[1][1]), kv[0])):
        when = parse_date(date)
        obs = tuple(Observation(SOURCE.id, f"{cid}:{i}", t["content"], when + timedelta(seconds=i), cid,
                                author_id=ROLES[t["role"]].id) for i, t in enumerate(turns))
        clock.now = when + timedelta(hours=1)
        memory.ingest(Batch((SOURCE,), obs, tuple(ROLES.values()), contexts=(Context(cid, "session", sid),)))
        by_context[cid] = [o.id for o in obs]
    return by_context


def questions(items, by_context):
    out = []
    for q in items:
        contexts, gold_sessions, gold_turns, unit = [], set(), set(), {}
        for sid, date, turns in zip(q["haystack_session_ids"], q["haystack_dates"], q["haystack_sessions"]):
            cid = context_id(sid, date, turns)
            contexts.append(cid)
            for i, oid in enumerate(by_context[cid]):
                unit[oid] = cid
                if turns[i].get("has_answer"):
                    gold_turns.add(oid)
            if sid in q["answer_session_ids"]:
                gold_sessions.add(cid)
        category = q["question_type"] + ("/abstention" if q["question_id"].endswith("_abs") else "")
        out.append(BenchQuestion(q["question_id"], q["question"], category, contexts, parse_date(q["question_date"]),
                                 {"session": gold_sessions, "turn": gold_turns}, {"session": unit}))
    return out
