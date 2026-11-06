"""Phase 8C.3: does TypeDB claim traversal add anything once the graph is populated automatically?

    uv run python -I -m gupi.benchmarks.phase8c_eval freeze
    uv run python -I -m gupi.benchmarks.phase8c_eval run --set dev --recording PATH --json PATH
    uv run python -I -m gupi.benchmarks.phase8c_eval run --set frozen --recording PATH --json PATH --approved-frozen-run

A keyword; B + conversational relationships; C = B + claim paths; D = B + text-only name matching; C+ = C + hypothesis
session links, labelled. Same scope, same k, same gold, same scorer. Questions are chosen by a mechanical rule from the
dataset's own labels and are stored as ids and hashes, never as text. Nothing here calls a model: claims come only from
a recording. Rules: docs/evaluation/phase-8c/scoring.md. Not a benchmark or leaderboard result.
"""

import argparse
import hashlib
import json
import random
import re
import statistics
import time
import uuid
from pathlib import Path

from gupi import evidence, identity, paths
from gupi.benchmarks import common, locomo, phase8c
from gupi.benchmarks.__main__ import Clock
from gupi.benchmarks.phase8c_manual import ManualExtractor
from gupi.formation import chat_extractor as chat
from gupi.formation.chat_extractor import ChatExtractor, Recording
from gupi.memory import Memory
from gupi.typedb.connection import connect

FROZEN = common.ROOT / "benchmarks" / "phase8c-frozen.json"
KS = tuple(phase8c.CONFIG["k"])
SYSTEMS = ("A-keyword", "B-conversational", "C-claim-paths", "D-name-control", "C+-unresolved-links")
PACK_FORMAT = "gupi.phase8c-pack/1"
PACK_CATEGORIES = ("multi-hop", "temporal", "provenance", "identity", "relationship", "conflict", "historical-change", "activity")
CAPITAL = re.compile(r"\b[A-Z][a-z]+\b")
MID_SENTENCE = re.compile(r"(?<=[a-z,;:] )[A-Z][a-z]+\b")


# --- the frozen question set ------------------------------------------------------------------------------------

def stratum(qa):
    """The selection rule, from the dataset's own labels only: 1 multi-hop with evidence in two or more sessions; 2
    temporal with any evidence. Nothing about GUPI, and no system's output, can affect it."""
    evidence_ids = {e.strip() for e in qa.get("evidence") or []}
    if qa["category"] == 1 and len(evidence_ids) >= 2 and len({e.split(":")[0] for e in evidence_ids}) >= 2:
        return "multi-hop"
    return "temporal" if qa["category"] == 2 and evidence_ids else None


def select(sample):
    return [{"id": f"{sample['sample_id']}:q{n}", "stratum": s,
             "question_sha256": hashlib.sha256(qa["question"].encode()).hexdigest(),
             "gold_turns": sorted({e.strip() for e in qa["evidence"]})}
            for n, qa in enumerate(sample["qa"]) if (s := stratum(qa))]


def freeze(path=FROZEN):
    """Written once. Prints counts only, and stores ids and hashes only."""
    if path.exists():
        raise FileExistsError(f"{path} exists: a frozen set is never rewritten")
    names = phase8c.CONFIG["evaluation"]
    items = [i for s in phase8c.samples(names) for i in select(s)]
    record = {"format": "gupi.phase8c-frozen/1", "source": "LoCoMo held-out conversations, first two in sorted order",
              "corpus_sha256": hashlib.sha256(locomo.PATH.read_bytes()).hexdigest(), "conversations": names,
              "rule": stratum.__doc__, "items": items}
    path.write_text(json.dumps(record, indent=1) + "\n")
    return {k: sum(i["stratum"] == k for i in items) for k in ("multi-hop", "temporal")}


def frozen_questions(all_questions, path=FROZEN):
    """The frozen items as BenchQuestions, after proving the corpus and every question are unchanged."""
    record = json.loads(path.read_text())
    if record["corpus_sha256"] != hashlib.sha256(locomo.PATH.read_bytes()).hexdigest():
        raise ValueError("the corpus differs from the one frozen")
    by_id = {q.id: q for q in all_questions}
    out = []
    for item in record["items"]:
        q = by_id[item["id"]]
        if hashlib.sha256(q.text.encode()).hexdigest() != item["question_sha256"]:
            raise ValueError(f"{item['id']} differs from the frozen question")
        q.category = item["stratum"]
        out.append(q)
    return out


def dev_questions(sample_list, all_questions):
    wanted = {i["id"]: i["stratum"] for s in sample_list for i in select(s)}
    out = [q for q in all_questions if q.id in wanted]
    for q in out:
        q.category = wanted[q.id]
    return out


def check_pack(pack):
    """Structural check of an independently authored pack (docs/evaluation/phase-8c/independent-authoring-brief.md)."""
    problems = [] if pack.get("format") == PACK_FORMAT else [f"format must be {PACK_FORMAT}"]
    turns = {t["id"] for s in pack.get("sessions", ()) for t in s["turns"]}
    if not pack.get("author") or pack.get("author_saw_gupi") is not False:
        problems.append("the pack must name its author and state author_saw_gupi: false")
    questions = pack.get("questions", ())
    if len({q["id"] for q in questions}) != len(questions):
        problems.append("question ids repeat")
    for q in questions:
        if q["category"] not in PACK_CATEGORIES:
            problems.append(f"{q['id']}: unknown category")
        if not q.get("answer") or not q.get("evidence") or not set(q["evidence"]) <= turns:
            problems.append(f"{q['id']}: needs an answer and evidence turns that exist")
    return problems


# --- the fairest text-only control ----------------------------------------------------------------------------

def name_words(texts):
    """Words capitalised in the middle of a sentence somewhere in the corpus: the control's only entity knowledge."""
    return {w for t in texts.values() for w in MID_SENTENCE.findall(t)}


def name_control(memory, question, contexts, budget, texts, known):
    """D: the same budget and merge as C, but two rounds of name matching over raw text. No claims, types, time or
    identity. Stronger matches first. If this equals C, typed claims are not what found the evidence."""
    base = paths.conversational(memory, question, contexts, budget)
    seeds = [i.observation_id for i in base.items if i.reasons[0] == "keyword"][:budget.seeds]
    inside = {o: known & set(CAPITAL.findall(texts[o])) for o in base.scope}
    names = (known & set(CAPITAL.findall(question))) | {n for s in seeds for n in inside[s]}
    linked = []
    for _ in range(budget.hops):
        hop = sorted((o for o, words in inside.items() if o not in linked and names & words), key=lambda o: (-len(names & inside[o]), o))
        linked += hop
        names = names | {n for o in hop for n in inside[o]}
    order = list(base.ids[:budget.keep])
    rest = paths.interleave(linked, base.ids[budget.keep:]) + linked + base.ids
    return list(dict.fromkeys(order + rest))[:budget.k]


# --- one question, every system ---------------------------------------------------------------------------------

def budget(**over):
    return paths.Budget(k=max(KS), **phase8c.CONFIG["budget"], **over)


def rank(memory, q, system, texts, known):
    if system == "A-keyword":
        return evidence.keyword(memory, q.text, q.contexts, max(KS)).ids, None
    if system == "B-conversational":
        return paths.conversational(memory, q.text, q.contexts, budget()).ids, None
    if system == "D-name-control":
        return name_control(memory, q.text, q.contexts, budget(), texts, known), None
    found = paths.retrieve(memory, q.text, q.contexts, budget(unresolved_links=system == "C+-unresolved-links"))
    return found.ids, found


def integrity(found, scope):
    """The must-be-zero list on what a claim system returned. Checked on real data, not only on a fixture."""
    bad = [f"{i.observation_id}: uncertain item shown as accepted" for i in found.items if i.tier == "accepted" and any(
        n.startswith(("not accepted", "pending", paths.UNCONFIRMED)) for n in i.notes)]
    bad += [f"{o}: outside the question's scope" for o in found.ids if o not in scope]
    bad += [f"{h.claim_id}: hop with no evidence" for p in found.paths for h in p.hops if not h.observations]
    bad += [f"{h.claim_id}: unconfirmed identity shown as firm" for p in found.paths for h in p.hops
            if any(n.startswith(paths.UNCONFIRMED) for n in h.notes) and h.tier != "unresolved"]
    return bad


def evaluate(memory, questions, texts):
    known, rows = name_words(texts), []
    for q in questions:
        gold = q.gold["turn"]
        if not gold:
            continue
        for system in SYSTEMS:
            t0 = time.perf_counter()
            ranked, found = rank(memory, q, system, texts, known)
            row = {"question": q.id, "stratum": q.category, "system": system, "seconds": time.perf_counter() - t0,
                   "ids": ranked, "gold": sorted(gold)}
            for k in KS:
                hit = set(ranked[:k]) & gold
                row[f"recall@{k}"], row[f"complete@{k}"] = len(hit) / len(gold), gold <= set(ranked[:k])
            if found is not None:
                row["severe"] = integrity(found, found.scope)
                row["overlap"] = [p.overlap for p in found.paths if len(p.hops) == 2]
                row["unresolved_items"] = sum(i.tier == "unresolved" for i in found.items)
            rows.append(row)
    return rows


# --- comparison ---------------------------------------------------------------------------------------------------

def paired(deltas):
    """Mean gain in points with a seeded bootstrap interval over questions: the same input always gives the same result."""
    d = phase8c.CONFIG["decision"]
    rng, n = random.Random(d["seed"]), len(deltas)
    means = sorted(sum(rng.choices(deltas, k=n)) / n for _ in range(d["bootstrap_samples"])) if n else [0.0]
    tail = (1 - d["confidence"]) / 2
    lo, hi = means[int(tail * len(means))], means[min(len(means) - 1, int((1 - tail) * len(means)))]
    return {"gain_points": round(100 * sum(deltas) / n, 1) if n else 0.0, "low": round(100 * lo, 1), "high": round(100 * hi, 1),
            "questions": n}


def shown(r):
    return r["gain_points"] >= phase8c.CONFIG["decision"]["minimum_gain_points"] and r["low"] > 0


def compare(rows, stratum_name, a="C-claim-paths", b="B-conversational"):
    pick = {(r["question"], r["system"]): r for r in rows if r["stratum"] == stratum_name}
    out = {}
    for k in KS:
        questions = sorted({q for q, s in pick if s == a and (q, b) in pick})
        out[f"recall@{k}"] = paired([pick[q, a][f"recall@{k}"] - pick[q, b][f"recall@{k}"] for q in questions])
    return out


def only_claims_found(rows, k):
    """Gold turns C placed in the top k that neither text-based system did: the plainest answer to 'did it find anything?'"""
    pick = {(r["question"], r["system"]): r for r in rows}
    found = 0
    for (q, s), r in pick.items():
        if s == "C-claim-paths":
            others = set(pick[q, "B-conversational"]["ids"][:k]) | set(pick[q, "D-name-control"]["ids"][:k])
            found += len((set(r["ids"][:k]) - others) & set(r["gold"]))
    return found


def summarise(rows):
    out = {"systems": {}, "comparisons": {}}
    for system in SYSTEMS:
        sel = [r for r in rows if r["system"] == system]
        secs = sorted(r["seconds"] for r in sel)
        metrics = [f"{m}@{k}" for k in KS for m in ("recall", "complete")]

        def mean(rs):
            return {m: round(statistics.mean(float(r[m]) for r in rs), 4) for m in metrics} | {"questions": len(rs)} if rs else {}
        out["systems"][system] = {"overall": mean(sel), "by_stratum": {s: mean([r for r in sel if r["stratum"] == s])
                                                                      for s in sorted({r["stratum"] for r in sel})},
                                  "latency_seconds": {"p50": round(secs[len(secs) // 2], 4), "p95": round(secs[int(len(secs) * .95)], 4)} if secs else {}}
    for s in sorted({r["stratum"] for r in rows}):
        out["comparisons"][s] = {"C over B": compare(rows, s), "C over D": compare(rows, s, b="D-name-control"),
                                 "C+ over C": compare(rows, s, "C+-unresolved-links", "C-claim-paths")}
    primary = out["comparisons"].get("multi-hop", {})
    out["decision"] = {f"recall@{k}": bool(primary) and shown(primary["C over B"][f"recall@{k}"]) and shown(primary["C over D"][f"recall@{k}"])
                       for k in KS}
    out["gold_turns_only_claims_found"] = {f"top{k}": only_claims_found(rows, k) for k in KS}
    out["severe"] = [x for r in rows for x in r.get("severe", ())]
    c = [o for r in rows if r["system"] == "C-claim-paths" for o in r.get("overlap", ())]
    out["overlap_labels"] = {k: c.count(k) for k in ("confirmed", "presumed", "none", "unknown")}
    return out


def adjudication_sample(memory, n, seed=8):
    """A random sample of formed claims for someone else to judge. Quotes the dataset, so it goes only into `.data/`.
    Model-assisted extraction is not independently verified until someone other than the builder has judged this."""
    claims = sorted((c for c in memory.all_claims() if c.type != "identity"), key=lambda c: c.id)
    chosen = random.Random(seed).sample(claims, min(n, len(claims)))
    return [{"claim": c.id, "type": c.type, "quote": c.evidence[0].quote, "values": {k: str(v) for k, v in c.values.items()},
             "commitment": c.commitment, "attribution": c.attribution_mode} for c in chosen]


def run(args):
    names = phase8c.CONFIG["development" if args.set == "dev" else "evaluation"]
    driver, db, clock = connect(), f"gupi-bench-phase8c-{uuid.uuid4().hex[:8]}", Clock()
    memory = Memory.open(db, packs=("core", "people"), driver=driver, create=True, clock=clock)
    try:
        names = args.conversations or names
        sample_list = phase8c.samples(names)
        # replay only: this module can never spend
        extractor = ManualExtractor(args.responses) if args.responses else ChatExtractor(Recording(args.recording))
        observations, stopped = phase8c.build(memory, clock, sample_list, extractor)
        turn_ids = {(o.record_key.split(":", 1)[0], o.record_key.split(":", 1)[1]): o.id for o in observations}
        everything, _ = locomo.questions(sample_list, turn_ids)
        questions = dev_questions(sample_list, everything) if args.set == "dev" else frozen_questions(everything)
        links = 0
        for s in sample_list:
            sid = s["sample_id"]
            contexts = [f"locomo:{sid}:s{i}" for i, _, _ in locomo.sessions(s)]
            links += len(identity.link_sessions(memory, contexts).linked)
        rows = evaluate(memory, questions, {o.id: o.content for o in observations})
        gold = {g for q in questions for g in q.gold["turn"]}
        result = {"set": args.set, "prompt": chat.PROMPT_HASH, "run_stopped": stopped, "session_links": links,
                  "conversations": names, "source": "manual subscription session" if args.responses else "recording",
                  "stopped": dict(getattr(extractor, "lost", {})), "stopped_that_would_link": dict(getattr(extractor, "lost_links", {})),
                  "tally": extractor.tally.as_dict(), "graph": phase8c.graph_report(memory, observations, gold),
                  "summary": summarise(rows), "note": "Evidence retrieval only; not a benchmark or leaderboard result."}
        print(json.dumps(result, indent=1))
        if args.json:
            Path(args.json).write_text(json.dumps(result, indent=1) + "\n")
        if args.sample:
            Path(args.sample).write_text(json.dumps(adjudication_sample(memory, 100), indent=1, ensure_ascii=False) + "\n")
    finally:
        driver.databases.get(db).delete()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("command", choices=("freeze", "run"))
    p.add_argument("--set", choices=("dev", "frozen"), default="dev")
    p.add_argument("--recording")
    p.add_argument("--responses", help="manual lines, outside the repository (phase8c_manual)")
    p.add_argument("--conversations", nargs="+")
    p.add_argument("--json")
    p.add_argument("--sample", help="write the adjudication sample here (not inside the repository's tracked files)")
    p.add_argument("--approved-frozen-run", action="store_true")
    args = p.parse_args(argv)
    if args.command == "freeze":
        print(json.dumps(freeze()))
        return 0
    if args.set == "frozen" and not args.approved_frozen_run:
        raise SystemExit("not started: the frozen set runs once, with the owner's approval (--approved-frozen-run)")
    if args.set == "frozen" and args.responses:
        raise SystemExit("not started: manual replies are development only")
    for path in (args.recording, args.sample, args.responses):
        if path and common.ROOT.resolve() in Path(path).resolve().parents and phase8c.DATA.resolve() not in Path(path).resolve().parents:
            raise SystemExit("not started: recordings, replies and samples quote the dataset and must not be in tracked files")
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
