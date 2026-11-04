"""Phase 7A: rules:v2 on every sampled turn, against the frozen annotations (domain coverage, failure stages).

    uv run python -I -m gupi.benchmarks.diagnosis.classify --json docs/evaluation/phase-7a/classification.json

Each turn gets the observation the adapter would build (same text, author and context). Any candidate goes
through the candidate store in a disposable database, so stages 8-10 are observed rather than assumed.
The representative and targeted samples are reported separately. No dataset text is written.
"""

import argparse
import json
import sys
import uuid
from collections import Counter
from datetime import datetime, timedelta

from gupi.benchmarks import longmemeval
from gupi.benchmarks.diagnosis import audit, sample
from gupi.benchmarks.e2e import common
from gupi.extraction.contract import referent_id
from gupi.formation import store
from gupi.formation.rules_v2 import DOMAIN_VERB, RulesV2
from gupi.memory import Memory
from gupi.records import Batch, Context, Observation, Referent, Source
from gupi.typedb.connection import connect

ANNOTATIONS = sample.OUT.parent / "annotations.json"


def observation(dataset, t, text):
    at = datetime.fromisoformat(t["at"])
    if dataset == "locomo":
        sid = t["conversation"]
        return Observation("src:locomo", t["key"], text, at, f"locomo:{sid}:s{t['session']}",
                           author_id=referent_id(f"locomo:{sid}", "person", "speaker-" + t["speaker_is"]))
    return Observation(longmemeval.SOURCE.id, t["key"], text, at, t["conversation"],
                       author_id=longmemeval.ROLES[t["speaker_is"]].id)


def through_store(driver, obs, cset):
    db, clock = f"gupi-7a-cls-{uuid.uuid4().hex[:8]}", common.Clock(obs.observed_at)
    memory = Memory.open(db, packs=("core", "people"), driver=driver, create=True, clock=clock)
    try:
        memory.ingest(Batch((Source(obs.source_id, "conversation"),), (obs,), (Referent(obs.author_id, "person", "author"),),
                            contexts=(Context(obs.context_id, "session"),)))
        clock.now = obs.observed_at + timedelta(minutes=1)
        sub = store.submit(memory, obs, cset)
        return {"invalid": len(sub.invalid), "statuses": [store.get(memory, c).status for c in sub.stored]}
    finally:
        driver.databases.get(db).delete()


def summarise(turns):
    facts = [f for t in turns for f in t["facts"]]
    cats = Counter(f["category"] for f in facts)
    return {"turns": len(turns),
            "turns_with_any_memory": sum(bool(t["facts"]) for t in turns),
            "turns_with_supported_A": sum(any(f["category"] == "A" for f in t["facts"]) for t in turns),
            "turns_with_ambiguous_A_or_B": sum(any(f["category"] == "A?" for f in t["facts"]) for t in turns),
            "turns_with_representable_unsupported_B": sum(any(f["category"] == "B" for f in t["facts"]) for t in turns),
            "turns_with_no_relevant_information_C": sum(not t["facts"] for t in turns),
            "assertions": len(facts), "assertions_by_category": dict(cats),
            "assertions_by_stage": dict(Counter(str(f["observed_stage"]) for f in facts)),
            "assertions_needing": dict(Counter(n.split(" (")[0] for f in facts for n in f["needs"])),
            "assertions_about": dict(Counter(f["about"] for f in facts)),
            "explicit_vs_implicit": dict(Counter(f["explicit"] for f in facts)),
            "turns_with_domain_verb": sum(t["domain_verbs"] != [] for t in turns),
            "candidates": sum(t["extractor"]["candidates"] for t in turns)}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--json")
    args = p.parse_args(argv)
    ann = json.loads(ANNOTATIONS.read_text())
    s = json.loads(sample.OUT.read_text())
    texts = sample.texts()
    driver = connect()
    ex = RulesV2()
    result = {"meta": {**common.meta("classification", "Phase 7A classification"), "phase": "7A"}, "results": {}}
    for dataset, parts in ann["datasets"].items():
        for part, turns in parts.items():
            info = {t["key"]: t for t in s["datasets"][dataset][part]}
            rows = []
            for a in turns:
                t = info[a["key"]]
                obs = observation(dataset, t, texts[(dataset, a["key"])])
                cset, report = ex.extract(obs)
                stored = through_store(driver, obs, cset) if cset.candidates else None
                facts = []
                for f in a["facts"]:
                    # the observed stage: the annotated one unless the extractor produced something for this turn
                    observed = f["stage"] if not cset.candidates else "check: candidates exist for this turn"
                    facts.append({**f, "observed_stage": observed})
                rows.append({"key": a["key"], "stratum": t["stratum"], "chars": t["chars"], "facts": facts,
                             "domain_verbs": sorted({v.lower() for v in DOMAIN_VERB.findall(obs.content)}),
                             "extractor": {"candidates": len(cset.candidates),
                                           "candidate_kinds": [(c.claim_type, [p.role for p in c.participants]) for c in cset.candidates],
                                           "rejected_clauses": [audit.why_no_pattern(r[0]) if r[1].startswith(audit.NO_PATTERN) else r[1]
                                                                for r in report.rejected]},
                             "store": stored})
            result["results"][f"{dataset}/{part}"] = {"summary": summarise(rows), "rows": rows}
    text = json.dumps(result, indent=1, default=str) + "\n"
    if args.json:
        open(args.json, "w").write(text)
    print(json.dumps({k: v["summary"] for k, v in result["results"].items()}, indent=1))


if __name__ == "__main__":
    sys.exit(main())
