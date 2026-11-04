"""D5 LoCoMo and D6 LongMemEval: layers A (formation), B (evidence retrieval) and D (operations).

The Phase 5 adapters, retrievers and metrics are used unchanged; the only difference from Phase 5 is that
every turn also goes through rules:v2 and the candidate store, so the structured retriever sees whatever
claims GUPI formed. No answers are generated: these are retrieval results, not LoCoMo or LongMemEval scores.
Dataset content is never written to results (ids, counts and metrics only).
"""

import json
import time
from datetime import timedelta

from gupi.benchmarks import common as bcommon
from gupi.benchmarks import locomo, longmemeval
from gupi.benchmarks.e2e import common, pipeline
from gupi.formation import store
from gupi.formation.rules_v2 import DOMAIN_VERB
from gupi.memory import Memory
from gupi.records import Observation

PHASE5 = bcommon.ROOT / "docs" / "evaluation" / "phase-5"


def _extract_and_submit(memory, clock, observations, thread_of):
    """rules:v2 over every observation in order (prior = earlier sets in the same thread), store.submit for
    those with candidates. Returns (per-observation info, timings)."""
    info, timings, prior = {}, {"extract": 0.0, "submit": 0.0}, {}
    for o in observations:
        t0 = time.perf_counter()
        cset, report = pipeline.EXTRACTOR.extract(o, prior=tuple(prior.setdefault(thread_of(o), [])))
        timings["extract"] += time.perf_counter() - t0
        prior[thread_of(o)].append(cset)
        entry = {"candidates": [c.id for c in cset.candidates], "domain_verb": bool(DOMAIN_VERB.search(o.content)),
                 "unparsed_in_domain": len(report.rejected)}
        if cset.candidates:
            clock.now = o.observed_at + timedelta(minutes=30)
            t0 = time.perf_counter()
            store.submit(memory, o, cset)
            timings["submit"] += time.perf_counter() - t0
        info[o.id] = entry
    return info, timings


def _formation_summary(memory, info):
    ids = [c for e in info.values() for c in e["candidates"]]
    return {"observations": len(info), "with_candidates": sum(bool(e["candidates"]) for e in info.values()),
            "candidates": len(ids), "observations_with_domain_verb": sum(e["domain_verb"] for e in info.values()),
            "unparsed_in_domain_sentences": sum(e["unparsed_in_domain"] for e in info.values()),
            "policy_outcomes": pipeline.first_decisions(memory, ids) if ids else {}}


def _attribute(questions, rows, info, claim_obs):
    """For the GUPI structured arm: what happened to each question's gold turns (earliest stage)."""
    top = {(r["question"], r["system"]): r for r in rows if r["unit"] == "turn"}
    out = {"questions": 0, "by_stage": {}, "turn_states": {}}
    for q in questions:
        gold = q.gold.get("turn") or set()
        if not gold:
            continue
        out["questions"] += 1
        states = []
        for t in gold:
            e = info.get(t, {})
            if t in claim_obs:
                s = "claim formed"
            elif e.get("candidates"):
                s = "candidate only"
            elif e.get("unparsed_in_domain"):
                s = "in-domain sentence not parsed"
            elif e.get("domain_verb"):
                s = "domain verb, no domain statement"
            else:
                s = "outside the extractor's domain"
            states.append(s)
            out["turn_states"][s] = out["turn_states"].get(s, 0) + 1
        r = top.get((q.id, "structured"))
        hit = r is not None and r["recall@10"] > 0
        if any(s == "claim formed" for s in states):
            stage = "retrieved" if hit else "6 retrieval missed stored evidence"
        elif any(s == "candidate only" for s in states):
            stage = "4 formation withheld"
        else:
            stage = "2 extraction missed (no candidate from any gold turn)"
        out["by_stage"][stage] = out["by_stage"].get(stage, 0) + 1
    return out


def _with_precision(rows, questions):
    sizes = {(q.id, unit): len(g) for q in questions for unit, g in q.gold.items()}
    for r in rows:
        r["precision@5"] = round(r["recall@5"] * sizes[(r["question"], r["unit"])] / 5, 6)
    return rows


def _precision_summary(rows):
    out = {}
    for r in rows:
        out.setdefault(r["unit"], {}).setdefault(r["system"], []).append(r["precision@5"])
    return {u: {s: round(sum(v) / len(v), 4) for s, v in d.items()} for u, d in out.items()}


def _reproduction(rows, phase5_file):
    path = PHASE5 / phase5_file
    if not path.exists():
        return None
    old = {(r["question"], r["system"], r["unit"]): r for r in json.loads(path.read_text())["rows"]}
    same = differ = absent = 0
    examples = []
    for r in rows:
        o = old.get((r["question"], r["system"], r["unit"]))
        if o is None:
            absent += 1
        elif all(abs(o[k] - r[k]) < 1e-9 for k in ("recall@1", "recall@5", "recall@10", "mrr")):
            same += 1
        else:
            differ += 1
            if len(examples) < 10:
                examples.append({"question": r["question"], "system": r["system"], "unit": r["unit"],
                                 "phase5_recall@5": o["recall@5"], "now_recall@5": r["recall@5"]})
    return {"compared_with": f"docs/evaluation/phase-5/{phase5_file}", "identical": same, "different": differ,
            "not_in_phase5": absent, "examples": examples}


def _claim_observations(memory):
    from typedb.driver import TransactionType

    from gupi import typeql
    from gupi.typedb.connection import transaction
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        docs = typeql.documents(tx, 'match $c isa claim, has candidate-id $k; evidence (supported: $c, support: $o); '
                                    'fetch { "o": $o.gupi-id };')
    return {d["o"] for d in docs}


def run_locomo(driver, label, split, systems, embedder=None, limit=None):
    db, clock = common.database_name(f"locomo-{split}"), common.Clock()
    memory = Memory.open(db, packs=("core", "people"), driver=driver, create=True, clock=clock)
    timings = {}
    try:
        data = locomo.load(split)
        t0 = time.perf_counter()
        turn_ids, observations = locomo.ingest(memory, clock, data)
        timings["ingest_seconds"] = time.perf_counter() - t0
        sample_of = {o.id: o.record_key.split(":")[0] for o in observations}
        info, t = _extract_and_submit(memory, clock, observations, lambda o: sample_of[o.id])
        timings.update({f"{k}_seconds": v for k, v in t.items()})
        timings["extract_turns_per_second"] = round(len(observations) / t["extract"], 1) if t["extract"] else None
        qs, missing = locomo.questions(data, turn_ids)
        if limit:
            qs = qs[:limit]
        contexts = sorted({c for q in qs for c in q.contexts})
        timings["database_bytes_before_embeddings"] = common.size(memory)
        if embedder is not None:
            from gupi import vectors
            t0 = time.perf_counter()
            timings["embeddings_written"] = vectors.store(memory, embedder, contexts)
            timings["embedding_seconds"] = time.perf_counter() - t0
        timings["database_bytes"] = common.size(memory)
        clock.now = clock.now.replace(year=2030)
        t0 = time.perf_counter()
        rows = _with_precision(bcommon.run_questions(memory, qs, systems, embedder), qs)
        timings["retrieval_seconds"] = time.perf_counter() - t0
        timings["peak_python_rss_bytes"] = bcommon.peak_rss_bytes()
        claim_obs = _claim_observations(memory)
        return {"meta": common.meta(label, f"D5 LoCoMo {split}"), "dataset": "locomo", "split": split,
                "questions": len(qs), "limit": limit, "evidence_ids_not_found": missing, "systems": systems,
                "note": "Evidence retrieval only; not an official LoCoMo score. No answers generated.",
                "formation": _formation_summary(memory, info), "database": common.counts(memory),
                "timings": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in timings.items()},
                "summary": bcommon.summarise(rows), "precision@5": _precision_summary(rows),
                "attribution_structured_arm": _attribute(qs, rows, info, claim_obs),
                "reproduction": None if limit else _reproduction(rows, f"locomo-{split}.json"),
                "rows": rows}
    finally:
        driver.databases.get(db).delete()


def _lme_observations(items):
    """The observations longmemeval.ingest creates, rebuilt identically (same ids), with answer-turn flags."""
    versions = {}
    for q in items:
        for sid, date, turns in zip(q["haystack_session_ids"], q["haystack_dates"], q["haystack_sessions"]):
            versions.setdefault(longmemeval.context_id(sid, date, turns), (sid, date, turns))
    out = []
    for cid, (sid, date, turns) in sorted(versions.items(), key=lambda kv: (longmemeval.parse_date(kv[1][1]), kv[0])):
        when = longmemeval.parse_date(date)
        for i, t in enumerate(turns):
            out.append((Observation(longmemeval.SOURCE.id, f"{cid}:{i}", t["content"], when + timedelta(seconds=i), cid,
                                    author_id=longmemeval.ROLES[t["role"]].id), bool(t.get("has_answer"))))
    return out


def longmemeval_extraction_only(label, split="heldout", limit=None):
    """Layer A over every held-out history, in memory (no TypeDB): what rules:v2 would submit."""
    items = longmemeval.load(split)[:limit]
    obs = _lme_observations(items)
    t0 = time.perf_counter()
    n_cand, with_cand, answer_turns, answer_with_cand, domain = 0, 0, 0, 0, 0
    kinds = {}
    for o, is_answer in obs:
        cset, _ = pipeline.EXTRACTOR.extract(o)
        n_cand += len(cset.candidates)
        with_cand += bool(cset.candidates)
        answer_turns += is_answer
        answer_with_cand += is_answer and bool(cset.candidates)
        domain += bool(DOMAIN_VERB.search(o.content))
        for c in cset.candidates:
            k = f"{c.claim_type}/{c.polarity}/{c.modality}/{c.commitment}"
            kinds[k] = kinds.get(k, 0) + 1
    seconds = time.perf_counter() - t0
    return {"meta": common.meta(label, "D6 LongMemEval held-out, extraction only"), "questions": len(items),
            "turns": len(obs), "turns_with_domain_verb": domain, "turns_with_candidates": with_cand,
            "candidates": n_cand, "candidate_kinds": kinds, "answer_turns": answer_turns,
            "answer_turns_with_candidates": answer_with_cand, "extract_seconds": round(seconds, 2),
            "turns_per_second": round(len(obs) / seconds, 1), "peak_python_rss_bytes": bcommon.peak_rss_bytes()}


def run_longmemeval_subset(driver, label, systems=("keyword", "structured"), split="heldout", limit=None):
    db, clock = common.database_name("lme-subset"), common.Clock()
    memory = Memory.open(db, packs=("core", "people"), driver=driver, create=True, clock=clock)
    timings = {}
    try:
        wanted = set(next(a["embedding_subset"] for a in bcommon.CONFIG["amendments"] if "embedding_subset" in a))
        items = [q for q in longmemeval.load(split) if split != "heldout" or q["question_id"] in wanted][:limit]
        t0 = time.perf_counter()
        by_context = longmemeval.ingest(memory, clock, items)
        timings["ingest_seconds"] = time.perf_counter() - t0
        observations = [o for o, _ in _lme_observations(items)]
        assert {o.id for o in observations} == {i for ids in by_context.values() for i in ids}
        info, t = _extract_and_submit(memory, clock, observations, lambda o: o.context_id)
        timings.update({f"{k}_seconds": v for k, v in t.items()})
        qs = longmemeval.questions(items, by_context)
        timings["database_bytes"] = common.size(memory)
        clock.now = clock.now.replace(year=2030)
        t0 = time.perf_counter()
        rows = _with_precision(bcommon.run_questions(memory, qs, list(systems), None), qs)
        timings["retrieval_seconds"] = time.perf_counter() - t0
        timings["peak_python_rss_bytes"] = bcommon.peak_rss_bytes()
        return {"meta": common.meta(label, "D6 LongMemEval held-out subset (64)"), "dataset": "longmemeval",
                "questions": len(qs), "systems": list(systems),
                "note": "Evidence retrieval only; not an official LongMemEval score. Embedding and hybrid on this "
                        "subset: Phase 5 first run (docs/evaluation/phase-5/longmemeval-heldout-subset.json).",
                "formation": _formation_summary(memory, info), "database": common.counts(memory),
                "timings": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in timings.items()},
                "summary": bcommon.summarise(rows), "precision@5": _precision_summary(rows),
                "attribution_structured_arm": _attribute(qs, rows, info, _claim_observations(memory)),
                "reproduction": _reproduction(rows, "longmemeval-heldout-subset.json"), "rows": rows}
    finally:
        driver.databases.get(db).delete()
