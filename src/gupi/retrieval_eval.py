"""Retrieval benchmark: structured retrieval vs keyword-only retrieval on the frozen dataset
(tests/fixtures/retrieval). Offline; each configuration uses its own disposable database.

    uv run python -I -m gupi.retrieval_eval [--config gold|rules] [--json PATH]

Configurations:
- gold:  claims built from the gold annotations, so only retrieval and answering are measured.
- rules: claims extracted by the offline rule extractor, so extraction errors carry through (end to end).
A simulated reviewer applies the frozen decisions: claims matching an annotated claim get its decision
(accepted unless marked rejected or unreviewed); extracted claims matching no annotation are rejected.
Identities between referents with exactly the same name are accepted on 2025-09-01.

Keyword baseline (deliberately simple, text only): search with the question's names, a few words for the
claim type and any values; among passages received by the belief time that mention every fixed name (and
value), take the best one; answer FALSE if it contains "left", "stopped" or "no longer", otherwise TRUE;
for an open role, the answer is the first other capitalised name in that passage; no passage gives
NOT_YET_KNOWN. It has no notion of valid time, review status or contradiction.
"""

import argparse
import json
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from gupi.extraction.contract import normalise, referent_id
from gupi.extraction.pipeline import extract
from gupi.extraction.rules import NAME, RuleExtractor
from gupi.memory import Memory
from gupi.records import Batch, Claim, Context, Evidence, Mention, Observation, Referent, Source
from gupi.temporal import Answer, ValidTime
from gupi.typedb.connection import connect

DATA = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "retrieval"
NOW = datetime(2025, 10, 1, tzinfo=timezone.utc)
IDENTITY_DAY = datetime(2025, 9, 1, tzinfo=timezone.utc)
KINDS = {"report": "person", "manager": "person", "employee": "person", "employer": "organization", "subject": "person"}
TYPE_WORDS = {"employment": "joined works work left", "reporting": "reports reported reporting manager"}
NEGATIVE = ("left", "stopped", "no longer")
ABSTAIN = {Answer.UNKNOWN, Answer.NOT_YET_KNOWN}


class Clock:
    def __init__(self):
        self.now = datetime(2025, 1, 1, tzinfo=timezone.utc)

    def __call__(self):
        return self.now


def _utc(text):
    text = text if "T" in text else text + "T00:00:00Z"
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)


def _window(pair):
    return (None, None) if pair is None else (_utc(pair[0]), _utc(pair[1]))


def load():
    return json.loads((DATA / "world.json").read_text()), json.loads((DATA / "questions.json").read_text())


def _gold_key(message, ctype, roles):
    return (message, ctype, tuple(sorted((r, normalise(n)) for r, n in roles.items())))


def build(memory, clock, world, config):
    """Ingest the world in time order, extract or build claims, apply the simulated reviewer's decisions.
    Returns {observation id: message key}."""
    gold = {}
    for conv in world["conversations"]:
        for g in conv["gold"]["claims"]:
            gold[_gold_key(g["message"], g["type"], g["roles"])] = g
    messages = sorted(((m, conv) for conv in world["conversations"] for m in conv["messages"]), key=lambda x: x[0]["at"])
    key_of = {}
    for m, conv in messages:
        said = _utc(m["at"])
        source, context = Source(f"src:{conv['source']}", "conversation"), Context(f"conv:{conv['id']}", "conversation")
        obs = Observation(source.id, m["key"], m["text"], said, context.id)
        key_of[obs.id] = m["key"]
        clock.now = said + timedelta(hours=1)
        memory.ingest(Batch((source,), (obs,), contexts=(context,)))
        if config == "rules":
            claim_ids = extract(memory, RuleExtractor(), [obs]).claims
        else:
            claim_ids = _ingest_gold(memory, obs, context, [g for g in conv["gold"]["claims"] if g["message"] == m["key"]])
        clock.now = said + timedelta(hours=2)
        decisions = []
        for view in memory.claims(claim_ids):
            labels = _labels(memory, view)
            g = gold.get(_gold_key(m["key"], view.type, labels))
            if g is None or (view.values.get("job-title") and normalise(view.values["job-title"]) != normalise(g["values"].get("job-title", ""))):
                decisions.append((view.id, "rejected"))
            elif g.get("decision") != "unreviewed":
                decisions.append((view.id, "rejected" if g.get("decision") == "rejected" else "accepted"))
        if decisions:
            memory.review_many(decisions, "simulated-reviewer")
    clock.now = IDENTITY_DAY
    found = memory.suggest_identities()
    same = {(s.a, s.b) for s in found if s.reason.startswith("same name")}
    ids = [c.id for c in memory.identity_claims() if tuple(sorted(c.roles["same"])) in same]
    if ids:
        memory.review_many([(i, "accepted") for i in ids], "simulated-reviewer")
    clock.now = NOW
    return key_of


def _labels(memory, view):
    from gupi.query import _labels as labels_of
    from gupi.typedb.connection import transaction
    from typedb.driver import TransactionType
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        names = labels_of(tx, [x for refs in view.roles.values() for x in refs])
    return {r: names.get(refs[0], refs[0]) for r, refs in view.roles.items()}


def _ingest_gold(memory, obs, context, gold_claims):
    referents, mentions, claims = [], [], []
    for g in gold_claims:
        roles = {}
        for role, name in g["roles"].items():
            kind = KINDS[role]
            rid = referent_id(context.id, kind, name)
            roles[role] = rid
            referents.append(Referent(rid, kind, name))
            start = obs.content.index(name)
            mentions.append(Mention(obs.id, start, start + len(name), name, rid, method="gold"))
        fe, fl = _window(g["start"])
        te, tl = _window(g["end"])
        if g["ongoing"]:
            te, basis = obs.observed_at, "ongoing-at-observation"
        else:
            basis = "stated" if g["end"] else "unknown"
        claims.append(Claim(g["type"], roles, (Evidence(obs.id, 0, len(obs.content)),), ValidTime(fe, fl, te, tl),
                            values=dict(g["values"]), valid_to_basis=basis, method="gold", basis="explicit"))
    memory.ingest(Batch(referents=tuple(dict.fromkeys(referents)), mentions=tuple(dict.fromkeys(mentions)), claims=tuple(claims)))
    return [c.id for c in claims]


def structured(memory, q, semantics="v1"):
    started = time.perf_counter()
    r = memory.query_by_name(q["type"], q["roles"], _utc(q["valid_at"]),
                             _utc(q["believed_at"]) if q.get("believed_at") else NOW, q.get("values") or None,
                             semantics)
    return {"answer": r.answer, "binding": r.binding, "observations": [c.observation_id for c in r.citations],
            "seconds": time.perf_counter() - started}


def keyword(memory, q):
    started = time.perf_counter()
    names = [n for n in q["roles"].values() if n]
    values = list((q.get("values") or {}).values())
    believed_at = _utc(q["believed_at"]) if q.get("believed_at") else NOW
    hits = memory.search(" ".join(names + values + [TYPE_WORDS[q["type"]]]), k=5, believed_at=believed_at)
    relevant = [h for h in hits if all(n.lower() in h.content.lower() for n in names + values)]
    out = {"answer": Answer.NOT_YET_KNOWN, "binding": [], "observations": [], "seconds": 0.0}
    if relevant:
        top = relevant[0]
        out["observations"] = [top.observation_id]
        out["answer"] = Answer.FALSE if any(w in top.content.lower() for w in NEGATIVE) else Answer.TRUE
        if None in q["roles"].values() and out["answer"] is Answer.TRUE:
            others = [n for n in re.findall(NAME, top.content) if n not in names + values and n not in ("Since", "Correction")]
            out["binding"] = others[:1]
    out["seconds"] = time.perf_counter() - started
    return out


def score(questions, outputs, key_of):
    rows, correct, abstain_ok, abstain_n, unsupported, cp, cr, cited_n = [], 0, 0, 0, 0, [], [], 0
    for q in questions:
        o = outputs[q["id"]]
        gold = q["gold"]
        want = Answer[gold["answer"]]
        ok = o["answer"] is want and (not gold.get("binding") or o["binding"] == [gold["binding"]])
        correct += ok
        if want in ABSTAIN:
            abstain_n += 1
            abstain_ok += o["answer"] in ABSTAIN
            unsupported += o["answer"] not in ABSTAIN
        if gold.get("evidence"):
            cited = {key_of[i] for i in o["observations"]}
            g = set(gold["evidence"])
            cited_n += 1
            cp.append(len(cited & g) / len(cited) if cited else 0.0)
            cr.append(len(cited & g) / len(g))
        rows.append({"id": q["id"], "gold": gold["answer"] + (f" ({gold['binding']})" if gold.get("binding") else ""),
                     "got": o["answer"].name + (f" ({', '.join(o['binding'])})" if o["binding"] else ""), "correct": ok,
                     "cited": sorted(key_of[i] for i in o["observations"])})
    n = len(questions)
    return {"accuracy": round(correct / n, 3), "correct": correct, "questions": n,
            "abstention": {"correct": abstain_ok, "of": abstain_n},
            "unsupported_assertions": unsupported,
            "citation_precision": round(sum(cp) / cited_n, 3) if cited_n else None,
            "citation_recall": round(sum(cr) / cited_n, 3) if cited_n else None,
            "median_seconds": round(sorted(o["seconds"] for o in outputs.values())[n // 2], 4),
            "rows": rows}


def run(config, driver=None, semantics="v1"):
    driver = driver or connect()
    world, questions = load()
    db = f"gupi-eval-retrieval-{uuid.uuid4().hex[:8]}"
    clock = Clock()
    memory = Memory.open(db, packs=("core", "people"), driver=driver, create=True, clock=clock)
    try:
        key_of = build(memory, clock, world, config)
        return {"config": config, "semantics": semantics,
                "structured": score(questions, {q["id"]: structured(memory, q, semantics) for q in questions}, key_of),
                "keyword": score(questions, {q["id"]: keyword(memory, q) for q in questions}, key_of)}
    finally:
        driver.databases.get(db).delete()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Structured vs keyword retrieval on the frozen benchmark.")
    parser.add_argument("--config", choices=["gold", "rules", "both"], default="both")
    parser.add_argument("--semantics", choices=["v1", "v2"], default="v1",
                        help="answer semantics for the structured system (docs/adr/0009); scoring is unchanged")
    parser.add_argument("--json", help="write the full results to this file")
    args = parser.parse_args(argv)
    results = [run(c, semantics=args.semantics) for c in (["gold", "rules"] if args.config == "both" else [args.config])]
    for r in results:
        for system in ("structured", "keyword"):
            s = r[system]
            print(f"{r['config']:5} {r['semantics']} {system:10} accuracy {s['correct']}/{s['questions']}  abstained {s['abstention']['correct']}/"
                  f"{s['abstention']['of']}  unsupported {s['unsupported_assertions']}  citations P {s['citation_precision']} "
                  f"R {s['citation_recall']}  median {s['median_seconds']}s")
    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=2, default=str) + "\n")


if __name__ == "__main__":
    main()
