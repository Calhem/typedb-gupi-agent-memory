"""Phase 7A section 6: the same message through Path A (RulesV2.extract directly) and Path B (the LoCoMo and
LongMemEval dataset adapters and the Phase 6D extraction and store pathway).

    uv run python -I -m gupi.benchmarks.diagnosis.pathcompare --json docs/evaluation/phase-7a/probe-results.json

Synthetic probes are wrapped as a one-session LoCoMo conversation and as a one-session LongMemEval history;
sampled benchmark turns go through their real conversation or session. Benchmark text is never written:
for those turns only counts and statuses are recorded.
"""

import argparse
import json
import sys
import uuid
from datetime import timedelta

from gupi.benchmarks import locomo, longmemeval
from gupi.benchmarks.common import ROOT
from gupi.benchmarks.diagnosis import classify, sample
from gupi.benchmarks.e2e import common, conversational
from gupi.formation import store
from gupi.formation.rules_v2 import RulesV2
from gupi.memory import Memory
from gupi.records import Batch, Context, Observation, Referent, Source
from gupi.typedb.connection import connect

DATA = ROOT / "tests" / "fixtures" / "diagnosis" / "probes-v2.json"


def _memory(driver, now):
    db, clock = f"gupi-7a-path-{uuid.uuid4().hex[:8]}", common.Clock(now)
    return Memory.open(db, packs=("core", "people"), driver=driver, create=True, clock=clock), clock


def _describe(memory, candidates):
    out = []
    for c in candidates:
        s = store.get(memory, c.id)
        out.append({"type": c.claim_type, "roles": {p.role: p.surface for p in c.participants},
                    "times": sorted((t.kind, t.earliest and t.earliest.date().isoformat(), t.latest and t.latest.date().isoformat())
                                    for t in c.times),
                    "polarity": c.polarity, "modality": c.modality, "commitment": c.commitment,
                    "mode": c.attribution.mode, "asserted_by": c.attribution.asserted_by,
                    "relations": sorted(r.kind for r in c.relations),
                    "status": s.status if s else "not stored", "reason": s.decisions[-1].reason if s and s.decisions else None})
    return sorted(out, key=lambda x: json.dumps(x, sort_keys=True))


def path_a(driver, messages, said, author_label):
    """Direct: one observation per message, RulesV2.extract with earlier sets as prior, store.submit."""
    memory, clock = _memory(driver, said)
    try:
        author = "p:speaker"
        memory.ingest(Batch(referents=(Referent(author, "person", author_label),)))
        src, ctx, prior, last = Source("src:path-a", "chat"), Context("ctx:path-a", "conversation"), [], None
        for n, text in enumerate(messages):
            obs = Observation(src.id, f"m{n}", text, said + timedelta(seconds=n), ctx.id, author)
            memory.ingest(Batch(sources=(src,), observations=(obs,), contexts=(ctx,)))
            cset, report = RulesV2().extract(obs, prior=tuple(prior))
            prior.append(cset)
            clock.now = obs.observed_at + timedelta(minutes=30)
            sub = store.submit(memory, obs, cset) if cset.candidates else None
            last = (cset, report, sub, obs)
        cset, report, sub, obs = last
        return {"extracted": len(cset.candidates), "invalid": len(sub.invalid) if sub else 0,
                "not_extracted": len(report.rejected), "candidates": _describe(memory, cset.candidates)}
    finally:
        memory.driver.databases.get(memory.database).delete()


def _after(memory, observations, thread_of, target_id):
    """Run the Phase 6D pathway, then describe exactly the candidates it stored for the target turn."""
    info, _ = conversational._extract_and_submit(memory, memory.clock, observations, thread_of)
    stored = [store.get(memory, cid).candidate for cid in info[target_id]["candidates"]]
    return {"extracted": len(stored), "not_extracted": info[target_id]["unparsed_in_domain"],
            "candidates": _describe(memory, stored)}


def path_b_locomo(driver, messages, said, speaker):
    when = said.strftime("%I:%M %p on %d %B, %Y")
    s = {"sample_id": "probe", "qa": [], "conversation": {
        "speaker_a": speaker, "speaker_b": "Sam Reed", "session_1_date_time": when,
        "session_1": [{"speaker": speaker, "dia_id": f"D1:{n + 1}", "text": t} for n, t in enumerate(messages)]}}
    memory, clock = _memory(driver, said)
    try:
        _, observations = locomo.ingest(memory, clock, [s])
        return _after(memory, observations, lambda o: "probe", observations[-1].id)
    finally:
        memory.driver.databases.get(memory.database).delete()


def path_b_longmemeval(driver, messages, said):
    item = {"question_id": "probe", "haystack_session_ids": ["probe-s1"],
            "haystack_dates": [said.strftime("%Y/%m/%d (%a) %H:%M")],
            "haystack_sessions": [[{"role": "user", "content": t} for t in messages]]}
    memory, clock = _memory(driver, said)
    try:
        longmemeval.ingest(memory, clock, [item])
        observations = [o for o, _ in conversational._lme_observations([item])]
        return _after(memory, observations, lambda o: o.context_id, observations[-1].id)
    finally:
        memory.driver.databases.get(memory.database).delete()


def compare(a, b):
    keys = ("type", "roles", "times", "polarity", "modality", "commitment", "mode", "asserted_by", "relations", "status")
    strip = lambda cs: [{k: c[k] for k in keys} for c in cs]  # noqa: E731
    return strip(a["candidates"]) == strip(b["candidates"]) and a["extracted"] == b["extracted"]


def judge(expect, got):
    if expect is None:
        return "correct (nothing)" if not got["candidates"] else "wrong: extracted where nothing should be"
    for c in got["candidates"]:
        if c["type"] == expect["type"] and {r: s.casefold() for r, s in c["roles"].items()} == \
                {r: s.casefold() for r, s in expect["roles"].items()}:
            diffs = [f for f, want, have in (
                ("times", sorted(expect["times"]), sorted(k for k, *_ in c["times"])),
                ("mode", expect["mode"], c["mode"]), ("commitment", expect["commitment"], c["commitment"]),
                ("asserted_by", (expect.get("asserted_by") or "").casefold() or None, (c["asserted_by"] or "").casefold() or None),
                ("relations", sorted(expect.get("relations", [])), c["relations"])) if want != have]
            return "match" if not diffs else "match on type and roles; differs in " + ", ".join(diffs)
    return "wrong participants or type" if got["candidates"] else "missed"


def benchmark_turn(driver, ref, texts):
    """A sampled turn through Path A (adapter-equivalent observation) and Path B (its real conversation)."""
    s = json.loads(sample.OUT.read_text())
    t = next(x for part in ("representative", "targeted") for x in s["datasets"][ref["dataset"]][part] if x["key"] == ref["key"])
    text = texts[(ref["dataset"], ref["key"])]
    obs = classify.observation(ref["dataset"], t, text)
    cset, report = RulesV2().extract(obs)
    a = {"extracted": len(cset.candidates), "not_extracted": len(report.rejected)}
    memory, clock = _memory(driver, obs.observed_at)
    try:
        if ref["dataset"] == "locomo":
            conv = [x for x in locomo.load("dev") if x["sample_id"] == t["conversation"]]
            _, observations = locomo.ingest(memory, clock, conv)
            target = next(o for o in observations if o.record_key == ref["key"])
            info, _ = conversational._extract_and_submit(memory, clock, observations, lambda o: t["conversation"])
        else:
            items = [q for q in longmemeval.load("dev") if any(
                longmemeval.context_id(sid, d, ts) == t["conversation"]
                for sid, d, ts in zip(q["haystack_session_ids"], q["haystack_dates"], q["haystack_sessions"]))][:1]
            sid_idx = next(i for i, (sid, d, ts) in enumerate(zip(items[0]["haystack_session_ids"], items[0]["haystack_dates"],
                                                                  items[0]["haystack_sessions"]))
                           if longmemeval.context_id(sid, d, ts) == t["conversation"])
            one = {k: ([items[0][k][sid_idx]] if k.startswith("haystack") else items[0][k]) for k in items[0]}
            longmemeval.ingest(memory, clock, [one])
            observations = [o for o, _ in conversational._lme_observations([one])]
            target = next(o for o in observations if o.record_key == ref["key"])
            info, _ = conversational._extract_and_submit(memory, clock, observations, lambda o: o.context_id)
        b = {"extracted": len(info[target.id]["candidates"]), "not_extracted": info[target.id]["unparsed_in_domain"],
             "observation_text_identical_to_path_a": target.content == obs.content,
             "turns_in_path_b": len(observations)}
    finally:
        memory.driver.databases.get(memory.database).delete()
    return {"dataset": ref["dataset"], "key": ref["key"], "why": ref["why"], "path_a": a, "path_b": b,
            "same": a["extracted"] == b["extracted"]}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--json")
    args = p.parse_args(argv)
    data = json.loads(DATA.read_text())
    said = common.utc(data["said_at"])
    driver = connect()
    rows = []
    for probe in data["probes"]:
        messages = probe.get("context", []) + [probe["text"]]
        a = path_a(driver, messages, said, data["speaker"])
        bl = path_b_locomo(driver, messages, said, data["speaker"])
        bm = path_b_longmemeval(driver, messages, said)
        rows.append({"id": probe["id"], "text": probe["text"], "context": probe.get("context", []), "expect": probe["expect"],
                     "note": probe.get("note"), "path_a": a, "path_b_locomo": bl, "path_b_longmemeval": bm,
                     "verdict_path_a": judge(probe["expect"], a),
                     "path_b_locomo_same_as_a": compare(a, bl), "path_b_longmemeval_same_as_a": compare(a, bm)})
        print(f"{probe['id']} A:{rows[-1]['verdict_path_a']} | B-LoCoMo same {rows[-1]['path_b_locomo_same_as_a']} | "
              f"B-LME same {rows[-1]['path_b_longmemeval_same_as_a']} | {[(c['roles'], c['times'], c['mode'], c['commitment'], c['status']) for c in a['candidates']]}")
    texts = sample.texts()
    bench = [benchmark_turn(driver, ref, texts) for ref in data["benchmark_turns"]]
    for b in bench:
        print(b["key"], b["path_a"], b["path_b"])
    result = {"meta": {**common.meta("probes-v2", "Phase 7A path comparison"), "phase": "7A"},
              "probes": rows, "benchmark_turns": bench,
              "summary": {"probes": len(rows),
                          "path_a_verdicts": {v: sum(r["verdict_path_a"] == v for r in rows) for v in sorted({r["verdict_path_a"] for r in rows})},
                          "path_b_locomo_identical": sum(r["path_b_locomo_same_as_a"] for r in rows),
                          "path_b_longmemeval_identical": sum(r["path_b_longmemeval_same_as_a"] for r in rows),
                          "benchmark_turns_identical": sum(b["same"] for b in bench)}}
    if args.json:
        open(args.json, "w").write(json.dumps(result, indent=1, default=str) + "\n")
    print(json.dumps(result["summary"], indent=1))


if __name__ == "__main__":
    sys.exit(main())
