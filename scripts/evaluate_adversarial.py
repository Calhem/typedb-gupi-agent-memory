"""Phase 6C development-only adversarial evaluation (docs/evaluation/phase-6c-adversarial.md).

    uv run python -I scripts/evaluate_adversarial.py --json docs/evaluation/phase-6c-adversarial-first-run.json

For each case of tests/fixtures/formation/adversarial-v1.json, in its own disposable database: ingest the
messages, extract with rules:v2, form (with the case's reviewer approvals), then ask the question under v2.
Each measure is scored separately. Needs the TypeDB server; no LLM, no paid calls.
"""

import argparse
import json
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gupi.extraction.contract import referent_id  # noqa: E402
from gupi.formation.form import form  # noqa: E402
from gupi.formation.rules_v2 import RulesV2  # noqa: E402
from gupi.memory import Memory  # noqa: E402
from gupi.query import Question  # noqa: E402
from gupi.records import Batch, Context, Observation, Referent, Source  # noqa: E402
from gupi.typedb.connection import connect  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "formation" / "adversarial-v1.json"
MEASURES = ("temporal", "qualification", "attribution", "independence", "citations")


class Clock:
    now = None

    def __call__(self):
        return self.now


def when(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def person(name):
    return "p:" + re.sub(r"[^a-z]+", "-", name.lower()).strip("-")


def run_case(driver, case):
    db, clock = f"gupi-adv-{uuid.uuid4().hex[:8]}", Clock()
    clock.now = when("2025-01-01T00:00:00Z")
    memory = Memory.open(db, packs=("core", "people"), driver=driver, create=True, clock=clock)
    try:
        authors = {m["author"] for m in case["messages"] if m.get("author")}
        if authors:
            memory.ingest(Batch(referents=tuple(Referent(person(a), "person", a) for a in sorted(authors))))
        obs_key = {}
        for m in case["messages"]:
            ctx = Context(f"ctx:{case['id']}:{m.get('context', 'main')}", "conversation")
            src = Source(f"src:{case['id']}:{m.get('source', 'mail')}", m.get("source", "mail"))
            obs = Observation(src.id, m["key"], m["text"], when(m["at"]), ctx.id,
                              person(m["author"]) if m.get("author") else None)
            clock.now = obs.observed_at
            memory.ingest(Batch(sources=(src,), observations=(obs,), contexts=(ctx,)))
            obs_key[obs.id] = m["key"]
            cset, _ = RulesV2().extract(obs)
            approvals = {c.id: "reviewer-a" for c in cset.candidates} if m["key"] in case.get("approve", ()) else {}
            form(memory, obs, cset, approvals)
        q = case["question"]
        ctx_id = f"ctx:{case['id']}:{q.get('context', 'main')}"
        roles = {r: referent_id(ctx_id, kind, name) for r, (kind, name) in q["roles"].items()}
        clock.now = max(when(m["at"]) for m in case["messages"])
        res = memory.query(Question(q["type"], roles, when(q["at"]),
                                    when(q["believed_at"]) if q.get("believed_at") else None, semantics="v2"))
        qual = res.qualification
        return {"answer": res.answer.name, "standing": qual.standing, "qualifiers": sorted(qual.qualifiers),
                "asserters": sorted(qual.originators), "independent": qual.independent,
                "cited": sorted({obs_key.get(c.observation_id, "?") for c in res.citations}),
                "definitive": qual.definitive, "explanation": qual.explanation}
    finally:
        driver.databases.get(db).delete()


def score(case, got):
    e = case["expect"]
    checks = {"temporal": got["answer"] == e["answer"],
              "qualification": got["standing"] == e["standing"] and got["qualifiers"] == sorted(e["qualifiers"]),
              "attribution": got["asserters"] == sorted(e["asserters"]),
              "independence": got["independent"] == e["independent"],
              "citations": got["cited"] == sorted(e["cited"])}
    unsupported = got["definitive"] and not e["definitive"]
    return checks, unsupported


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json")
    args = parser.parse_args(argv)
    data = json.loads(DATA.read_text())
    driver = connect()
    rows, totals, unsupported, missed_definitive = [], {m: 0 for m in MEASURES}, 0, 0
    for case in data["cases"]:
        got = run_case(driver, case)
        checks, bad = score(case, got)
        for m, ok in checks.items():
            totals[m] += ok
        unsupported += bad
        missed_definitive += case["expect"]["definitive"] and not got["definitive"]
        rows.append({"id": case["id"], "about": case["about"], "expected": case["expect"], "got": got,
                     "checks": checks, "unsupported_definitive": bad})
        print(f"{case['id']} {'ok ' if all(checks.values()) and not bad else 'BAD'} {case['about']}: "
              + ", ".join(m for m, ok in checks.items() if not ok) + (" unsupported-definitive" if bad else ""))
    n = len(data["cases"])
    summary = {"cases": n, **{m: f"{totals[m]}/{n}" for m in MEASURES},
               "unsupported_definitive": f"{unsupported}/{n}",
               "unsupported_definitive_rate": round(unsupported / n, 3),
               "definitive_withheld_where_warranted": f"{missed_definitive}/{sum(c['expect']['definitive'] for c in data['cases'])}"}
    print(json.dumps(summary, indent=1))
    if args.json:
        Path(args.json).write_text(json.dumps({"summary": summary, "rows": rows}, indent=2, default=str) + "\n")


if __name__ == "__main__":
    main()
