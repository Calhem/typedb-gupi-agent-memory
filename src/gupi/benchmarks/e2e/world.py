"""D1: the frozen Phase 4 world and its 15 questions, answered end to end (layers A, B, C, D).

Every system sees the same 11 messages. GUPI configurations build their own database; the evidence-only
retrievers and the keyword answer baseline run over the end-to-end database (same observations). Gold is
read only by the scorer: systems get `common.public(question)`.
"""

import time
from datetime import timedelta

from gupi import evidence
from gupi import retrieval_eval as p4
from gupi.benchmarks.e2e import common, pipeline
from gupi.extraction.contract import normalise
from gupi.formation import store
from gupi.memory import Memory
from gupi.records import Batch, Context, Observation, Source

ANSWERING = ("gupi-e2e", "gupi-e2e-policy", "gupi-gold", "gupi-rules-v1", "keyword-answer")
RETRIEVERS = ("keyword", "embedding", "hybrid", "hybrid-unfiltered", "structured")
REVIEWER = "simulated-reviewer"
ABSTAIN = {"UNKNOWN", "NOT_YET_KNOWN"}


def _messages(world):
    return sorted(((m, conv) for conv in world["conversations"] for m in conv["messages"]), key=lambda x: x[0]["at"])


def _gold_claims(world):
    return {g["message"]: g for conv in world["conversations"] for g in conv["gold"]["claims"]}


def _matches(cand, g):
    return g is not None and cand["type"] == g["type"] and set(cand["roles"]) == set(g["roles"]) and all(
        normalise(cand["roles"][r]) == normalise(n) for r, n in g["roles"].items())


def build_e2e(memory, clock, world, reviewer=True):
    """Ingest in time order, extract with rules:v2, submit to the store, apply the pre-registered simulated
    reviewer (PLAN.md), accept same-name identities. Returns ({observation id: key}, trace, timings)."""
    gold = _gold_claims(world)
    key_of, trace, prior, timings, review_log = {}, {}, {}, {}, []
    for m, conv in _messages(world):
        said = p4._utc(m["at"])
        source, context = Source(f"src:{conv['source']}", "conversation"), Context(f"conv:{conv['id']}", "conversation")
        obs = Observation(source.id, m["key"], m["text"], said, context.id)
        key_of[obs.id] = m["key"]
        cset, report, sub = pipeline.ingest_extract_submit(
            memory, clock, obs, Batch((source,), (obs,), contexts=(context,)), prior.setdefault(conv["id"], []),
            received=said + timedelta(hours=1), timings=timings)
        prior[conv["id"]].append(cset)
        cands = [pipeline.summary(c) for c in cset.candidates]
        trace[m["key"]] = {"text": m["text"], "gold": gold.get(m["key"]), "candidates": cands,
                           "not_extracted": [list(r) for r in report.rejected],
                           "invalid_in_store": [list(x) for x in (sub.invalid if sub else [])]}
        if reviewer:
            clock.now = said + timedelta(hours=2)
            g = gold.get(m["key"])
            for c in cands:
                s = store.get(memory, c["id"])
                if s is None:
                    continue
                decision = (g or {}).get("decision", "accepted") if _matches(c, g) else None
                if s.status == "review":
                    if decision == "accepted":
                        store.review(memory, c["id"], "approve", REVIEWER, "matches the recorded decision")
                        review_log.append((m["key"], c["id"], "approve"))
                    elif decision in ("rejected", None):
                        store.review(memory, c["id"], "reject", REVIEWER,
                                     "recorded as rejected" if decision else "does not match what the message says")
                        review_log.append((m["key"], c["id"], "reject"))
                elif s.status == "formed" and decision == "rejected":
                    memory.review(s.claim_id, "rejected", REVIEWER, "recorded as rejected")
                    review_log.append((m["key"], c["id"], "claim rejected"))
    clock.now = p4.IDENTITY_DAY
    found = memory.suggest_identities()
    same = {(s.a, s.b) for s in found if s.reason.startswith("same name")}
    ids = [c.id for c in memory.identity_claims() if tuple(sorted(c.roles["same"])) in same]
    if ids:
        memory.review_many([(i, "accepted") for i in ids], REVIEWER)
    clock.now = p4.NOW
    for key, t in trace.items():
        for c in t["candidates"]:
            c["state"] = pipeline.stored_state(memory, c["id"])
            vt, why = pipeline.mapped_time(_candidate(memory, c["id"]))
            c["mapped_valid_time"] = _vt(vt) if vt else None
            c["unmappable"] = why
            c["believed_now"] = pipeline.believed(memory, c["state"].get("claim"), p4.NOW)
            claim = c["state"].get("claim")
            c["stored_valid_time"] = _vt(memory.claims([claim])[0].valid) if claim else None
    return key_of, trace, timings, review_log


def _candidate(memory, cid):
    s = store.get(memory, cid)
    return s.candidate if s else None


def _vt(vt):
    return [x.isoformat() if x else None for x in (vt.from_earliest, vt.from_latest, vt.to_earliest, vt.to_latest)]


def gold_vt(g, said):
    """The gold claim's valid time, converted exactly as Phase 4's gold configuration converts it."""
    fe, fl = p4._window(g["start"])
    te, tl = (said, None) if g["ongoing"] else p4._window(g["end"])
    return [x.isoformat() if x else None for x in (fe, fl, te, tl)]


def gupi_answer(memory, q, semantics="v2"):
    started = time.perf_counter()
    try:
        r = memory.query_by_name(q["type"], q["roles"], p4._utc(q["valid_at"]),
                                 p4._utc(q["believed_at"]) if q.get("believed_at") else p4.NOW,
                                 q.get("values") or None, semantics)
    except Exception as e:  # a missing answer, kept apart from an incorrect one
        return {"answer": None, "error": f"{type(e).__name__}: {e}", "binding": [], "observations": [],
                "seconds": time.perf_counter() - started}
    qual = r.qualification
    return {"answer": r.answer, "binding": r.binding, "observations": [c.observation_id for c in r.citations],
            "claims": [c.claim_id for c in r.citations], "seconds": time.perf_counter() - started,
            "standing": qual.standing if qual else None, "definitive": qual.definitive if qual else None,
            "qualifiers": sorted(qual.qualifiers) if qual else None,
            "explanation": next((b.explanation for b in r.bindings if b.explanation), None)}


def categories(q):
    gold = q["gold"]["answer"]
    out = ["temporal-status"]
    if gold == "CONTESTED":
        out.append("contradiction")
    if gold in ABSTAIN:
        out.append("abstention")
    if q.get("believed_at"):
        out.append("belief-time")
    if None in q["roles"].values():
        out.append("open-role")
    return out


def score(questions, outputs, key_of):
    """The frozen Phase 4 scorer, plus measures it lacks (missing vs incorrect, categories, qualification)."""
    present = [q for q in questions if outputs[q["id"]]["answer"] is not None]
    frozen = p4.score(present, {q["id"]: outputs[q["id"]] for q in present}, key_of) if present else None
    rows, by_cat, unsupported_def, vs_gold, nondirect = [], {}, 0, 0, 0
    frozen_rows = {r["id"]: r for r in (frozen["rows"] if frozen else [])}
    for q in questions:
        o, gold = outputs[q["id"]], q["gold"]
        missing = o["answer"] is None
        correct = (not missing) and frozen_rows[q["id"]]["correct"]
        name = None if missing else o["answer"].name
        definitive = name in ("TRUE", "FALSE")
        undeserved = definitive and (gold["answer"] in ABSTAIN | {"CONTESTED"} or
                                     (o.get("standing") not in (None, "direct")))
        unsupported_def += undeserved
        vs_gold += definitive and gold["answer"] in ABSTAIN | {"CONTESTED"}
        nondirect += definitive and o.get("standing") not in (None, "direct")
        cited = sorted(key_of[i] for i in o["observations"])
        g = set(gold.get("evidence") or [])
        row = {"id": q["id"], "categories": categories(q), "gold": gold["answer"], "gold_binding": gold.get("binding"),
               "got": name, "binding": o["binding"], "missing": missing, "error": o.get("error"), "correct": correct,
               "cited": cited, "gold_evidence": sorted(g),
               "citation_precision": (len(set(cited) & g) / len(cited) if cited else 0.0) if g else None,
               "citation_recall": len(set(cited) & g) / len(g) if g else None,
               "standing": o.get("standing"), "definitive_flag": o.get("definitive"), "qualifiers": o.get("qualifiers"),
               "unsupported_definitive": undeserved, "explanation": o.get("explanation"), "seconds": o["seconds"]}
        rows.append(row)
        for c in row["categories"]:
            b = by_cat.setdefault(c, {"correct": 0, "of": 0})
            b["of"] += 1
            b["correct"] += correct
    n = len(questions)
    standings = {}
    for r in rows:
        standings[str(r["standing"])] = standings.get(str(r["standing"]), 0) + 1
    return {"questions": n, "correct": sum(r["correct"] for r in rows), "missing": sum(r["missing"] for r in rows),
            "incorrect": sum(not r["correct"] and not r["missing"] for r in rows),
            "frozen_scorer": {k: v for k, v in (frozen or {}).items() if k != "rows"},
            "by_category": by_cat, "unsupported_definitive": unsupported_def,
            "unsupported_definitive_parts": {"definitive_where_gold_abstains_or_contested": vs_gold,
                                             "definitive_on_evidence_not_direct": nondirect}, "standings": standings,
            "latency": common.latency([r["seconds"] for r in rows]), "rows": rows}


def retrieval(memory, questions, key_of, contexts, embedder):
    """Evidence-only systems on the questions that have gold evidence (message units)."""
    obs_of = {k: o for o, k in key_of.items()}
    rows = []
    for q in questions:
        gold = {obs_of[k] for k in q["gold"].get("evidence") or []}
        if not gold:
            continue
        pq = common.public(q)
        asked = p4._utc(pq["believed_at"]) if pq.get("believed_at") else p4.NOW
        for system in RETRIEVERS:
            t0 = time.perf_counter()
            if system == "keyword":
                r = evidence.keyword(memory, pq["text"], contexts, 50)
            elif system == "embedding":
                r = evidence.embedding(memory, embedder, pq["text"], contexts, 50)
            elif system == "structured":
                r = evidence.structured(memory, pq["text"], contexts, asked, 50)
            else:
                r = evidence.hybrid(memory, embedder, pq["text"], contexts, asked, 50, 60,
                                    use_structure=(system == "hybrid"))
            secs = time.perf_counter() - t0
            m = {f"recall@{k}": len(set(r.ids[:k]) & gold) / len(gold) for k in (1, 5, 10)}
            m["precision@5"] = len(set(r.ids[:5]) & gold) / 5
            rows.append({"question": q["id"], "system": system, "categories": categories(q), "gold": len(gold),
                         "returned": len(r.ids), "top5": [key_of[i] for i in r.ids[:5]], "seconds": secs, **m})
    summary = {}
    for system in RETRIEVERS:
        sel = [r for r in rows if r["system"] == system]
        summary[system] = {k: round(sum(r[k] for r in sel) / len(sel), 3) for k in
                           ("recall@1", "recall@5", "recall@10", "precision@5")} | {
            "questions": len(sel), "latency": common.latency([r["seconds"] for r in sel])}
    return {"unit": "message", "note": "11 messages in all: recall@10 is close to guaranteed", "summary": summary,
            "rows": rows}


def evidence_states(questions, outputs, trace):
    """For each gold evidence message: cited / formed-not-cited / candidate only / text only."""
    out = {"cited": 0, "formed_not_cited": 0, "candidate_only": 0, "text_only": 0, "rows": []}
    for q in questions:
        cited = set(outputs[q["id"]].get("cited", []))
        for key in q["gold"].get("evidence") or []:
            t = trace[key]
            matched = [c for c in t["candidates"] if _matches(c, t["gold"])]
            if key in cited:
                state = "cited"
            elif any(c["state"].get("status") == "formed" and c["believed_now"] for c in matched):
                state = "formed_not_cited"
            elif t["candidates"]:
                state = "candidate_only"
            else:
                state = "text_only"
            out[state] += 1
            out["rows"].append({"question": q["id"], "message": key, "state": state})
    return out


def attribute(questions, scored, trace, gold_scored):
    """Earliest responsible stage (PLAN.md) for each incorrect or unsupported e2e answer, and for answers
    whose citations miss all gold evidence. Fixed rules; manual reassignments are made in the report."""
    gold_rows = {r["id"]: r for r in gold_scored["rows"]}
    out = []
    for q, r in zip(questions, scored["rows"]):
        cite_fail = r["gold_evidence"] and not set(r["cited"]) & set(r["gold_evidence"])
        if r["correct"] and not r["unsupported_definitive"] and not cite_fail:
            continue
        stages, notes = [], []
        if r["missing"]:
            stages.append(8)
            notes.append(f"no answer: {r['error']}")
        evidence_keys = r["gold_evidence"] or []
        for key in evidence_keys:
            t = trace[key]
            g = t["gold"]
            matched = [c for c in t["candidates"] if _matches(c, g)]
            if not t["candidates"]:
                stages.append(2)
                notes.append(f"{key}: no candidate extracted")
            elif not matched:
                stages.append(3)
                notes.append(f"{key}: extracted as {[(c['type'], c['roles']) for c in t['candidates']]}, gold {g['type']} {g['roles']}")
            else:
                c = matched[0]
                status = c["state"].get("status")
                if status != "formed":
                    stages.append(4)
                    notes.append(f"{key}: {status} ({c['state']['decisions'][-1][2] if c['state'].get('decisions') else ''})")
                elif c["stored_valid_time"] != c["mapped_valid_time"]:
                    stages.append(5)
                    notes.append(f"{key}: stored valid time {c['stored_valid_time']} differs from the candidate's {c['mapped_valid_time']}")
                elif c["mapped_valid_time"] != gold_vt(g, t['said']):
                    stages.append(3)
                    notes.append(f"{key}: valid time {c['mapped_valid_time']} vs gold {gold_vt(g, t['said'])}")
                elif key not in r["cited"] and key in gold_rows[q["id"]]["cited"]:
                    stages.append(6)
                    notes.append(f"{key}: formed and believed, not cited (gupi-gold cites it)")
                elif key not in r["cited"]:
                    notes.append(f"{key}: formed and believed; not cited, and gupi-gold does not cite it either")
        for key in r["cited"]:
            if key in evidence_keys:
                continue
            t = trace[key]
            g = t["gold"]
            formed = [c for c in t["candidates"] if c["state"].get("status") == "formed" and c["believed_now"]]
            for c in formed:
                if g is None or not _matches(c, g):
                    stages.append(3)
                    notes.append(f"{key}: cited claim {c['type']} {c['roles']} does not match the gold claim")
                elif g.get("decision") in ("rejected", "unreviewed"):
                    stages.append(4)
                    notes.append(f"{key}: formed by the policy although recorded as {g['decision']}")
        if not stages:
            same_on_gold = gold_rows[q["id"]]["got"] == r["got"]
            stages.append(7 if r["got"] != r["gold"] else 8)
            notes.append("evidence formed and cited as gold; the answer follows from the semantics"
                         + (" (gupi-gold gives the same answer)" if same_on_gold else " (gupi-gold differs)"))
        out.append({"question": q["id"], "gold": r["gold"], "got": r["got"], "correct": r["correct"],
                    "unsupported_definitive": r["unsupported_definitive"], "citation_failure": bool(cite_fail),
                    "earliest_stage": min(stages), "stages": sorted(set(stages)), "notes": notes})
    return out


def run(driver, label, embedder=None):
    world, questions = p4.load()
    result = {"meta": common.meta(label, "D1 world"), "systems": {}, "databases": {}}
    contexts = sorted({f"conv:{c['id']}" for c in world["conversations"]})
    said_of = {m["key"]: p4._utc(m["at"]) for m, _ in _messages(world)}
    dbs = []
    try:
        built = {}
        for name, reviewer in (("gupi-e2e", True), ("gupi-e2e-policy", False)):
            db, clock = common.database_name("world"), common.Clock()
            dbs.append(db)
            memory = Memory.open(db, packs=("core", "people"), driver=driver, create=True, clock=clock)
            t0 = time.perf_counter()
            key_of, trace, timings, review_log = build_e2e(memory, clock, world, reviewer)
            for k, t in trace.items():
                t["said"] = said_of[k]
            timings["build_total"] = time.perf_counter() - t0
            built[name] = (memory, key_of, trace)
            result["databases"][name] = {**common.counts(memory), "bytes": common.size(memory),
                                         "timings": {k: round(v, 4) for k, v in timings.items()},
                                         "reviews": review_log}
        for name, config in (("gupi-gold", "gold"), ("gupi-rules-v1", "rules")):
            db, clock = common.database_name("world"), p4.Clock()
            dbs.append(db)
            memory = Memory.open(db, packs=("core", "people"), driver=driver, create=True, clock=clock)
            key_of = p4.build(memory, clock, world, config)
            built[name] = (memory, key_of, None)
            result["databases"][name] = {**common.counts(memory), "bytes": common.size(memory)}
        for name in ("gupi-e2e", "gupi-e2e-policy", "gupi-gold", "gupi-rules-v1"):
            memory, key_of, _ = built[name]
            outputs = {q["id"]: gupi_answer(memory, common.public(q)) for q in questions}
            result["systems"][name] = score(questions, outputs, key_of)
        memory, key_of, trace = built["gupi-e2e"]
        outputs = {q["id"]: p4.keyword(memory, common.public(q)) for q in questions}
        result["systems"]["keyword-answer"] = score(questions, outputs, key_of)
        # gold isolation: the same system given the full question (with gold) answers identically
        again = {q["id"]: gupi_answer(memory, q) for q in questions}
        first = result["systems"]["gupi-e2e"]["rows"]
        result["checks"] = {"gold_does_not_change_answers": all(
            (again[r["id"]]["answer"].name if again[r["id"]]["answer"] else None) == r["got"] for r in first)}
        if embedder is not None:
            from gupi import vectors
            t0 = time.perf_counter()
            written = vectors.store(memory, embedder, contexts)
            result["databases"]["gupi-e2e"]["embedding"] = {"written": written, "seconds": round(time.perf_counter() - t0, 3)}
        result["retrieval"] = retrieval(memory, questions, key_of, contexts, embedder)
        result["evidence_states"] = evidence_states(questions, {r["id"]: r for r in first}, trace)
        result["attribution"] = attribute(questions, result["systems"]["gupi-e2e"], trace, result["systems"]["gupi-gold"])
        result["trace"] = {k: {**t, "said": t["said"].isoformat()} for k, t in trace.items()}
        result["checks"].update({
            "e2e_uses_candidate_store": result["databases"]["gupi-e2e"]["memory-candidate"] > 0,
            "e2e_claims_all_linked_to_store": result["databases"]["gupi-e2e"]["claims_with_candidate_but_no_store_link"] == 0,
            "baselines_see_same_observations": len({result["databases"][n]["observation"] for n in result["databases"]}) == 1,
        })
        return result
    finally:
        for db in dbs:
            if driver.databases.contains(db):
                driver.databases.get(db).delete()
