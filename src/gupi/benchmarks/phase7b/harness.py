"""Phase 7B offline harness: rules:v2.1 versus recorded model:candidate-v1 outputs, scored against gold
assertions in the annotation-template format (docs/evaluation/phase-7b/offline-harness.md).

    uv run python -I -m gupi.benchmarks.phase7b.harness <corpus folder> [--gold FILE] [--responses FILE]
        [--formation] [--json OUT]

The corpus folder holds passages.csv and the gold (assertions.csv, or --gold). Recorded responses are a JSON
file {"responses": {passage_id: response}}. Nothing here calls a model or the network; --formation also runs
every candidate through the candidate store in a disposable local TypeDB database. Extraction, validation and
formation results are kept separate. Semantic matches that rules cannot settle are listed for a person to
adjudicate; nothing is decided by an LLM.
"""

import argparse
import hashlib
import json
import re
import sys
import uuid
from datetime import datetime, timedelta, timezone
from math import sqrt
from pathlib import Path

from gupi.benchmarks.phase7b import annotations as ann
from gupi.formation import extractors
from gupi.formation.model_candidate import METHOD as MODEL_METHOD, RESPONSE_FORMAT, ModelCandidateV1
from gupi.formation.rules_v21 import PRONOUNS, reason_kind
from gupi.records import Observation

SCORER_VERSION = "phase7b-scorer/1"
SYSTEMS = ("rules:v2.1", MODEL_METHOD)
WEAKER_MODES = {"reported", "quoted", "forwarded", "rumour", "unattributed"}


# --- corpus ------------------------------------------------------------------------------------------

def _slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def load(folder, gold=None, responses=None):
    folder = Path(folder)
    _, passages = ann.read(folder / "passages.csv")
    gold_path = Path(gold) if gold else folder / "assertions.csv"
    _, gold_rows = ann.read(gold_path)
    problems = ann.check_passages(*ann.read(folder / "passages.csv")) + ann.check_assertions(
        gold_path.name, ann.read(gold_path)[0], gold_rows, {p["passage_id"]: p for p in passages})
    if problems:
        raise ValueError("the corpus fails the structural check:\n" + "\n".join(problems))
    recorded = json.loads(Path(responses).read_text())["responses"] if responses else {}
    files = [folder / "passages.csv", gold_path] + ([Path(responses)] if responses else [])
    hashes = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
    order = sorted(passages, key=lambda p: (p["thread_id"] or p["passage_id"], int(p["turn"] or 0), p["passage_id"]))
    return order, gold_rows, recorded, hashes


def observation(p):
    day = datetime.fromisoformat(p["document_date"]).replace(tzinfo=timezone.utc) if p["document_date"] not in ("", "unknown") \
        else datetime(2000, 1, 1, tzinfo=timezone.utc)
    when = day + timedelta(hours=9, minutes=int(p["turn"] or 0))
    author = f"p:{_slug(p['stated_author'])}" if p["stated_author"] else None
    return Observation(f"src:7b:{p['set']}", p["passage_id"], p["text"], when,
                       f"ctx:7b:{p['thread_id'] or p['passage_id']}", author)


# --- extraction ----------------------------------------------------------------------------------------

def extract(passages, system, recorded, schema=None):
    """{passage id: (CandidateSet, [outcome dicts])}, threads read in order."""
    out, prior = {}, {}
    model = ModelCandidateV1(recorded)
    for p in passages:
        obs = observation(p)
        thread = prior.setdefault(p["thread_id"] or p["passage_id"], [])
        if system == MODEL_METHOD:
            cset, report = model.extract(obs, prior=tuple(thread), schema=schema, response=recorded.get(p["passage_id"]))
            outcomes = [{"kind": o["kind"], "evidence": o.get("evidence") or "", "detail": o["detail"]} for o in report.outcomes]
            flags = report.flags
        else:
            cset, report = extractors.get(system).extract(obs, prior=tuple(thread), schema=schema)
            outcomes = [{"kind": reason_kind(r), "evidence": t, "detail": r} for t, r in report.rejected]
            flags = []
        thread.append(cset)
        out[p["passage_id"]] = (obs, cset, outcomes, flags)
    return out


def formation(passages, extracted, driver):
    """Every candidate through store.submit in a disposable database. {candidate id: status}."""
    from gupi.formation import store
    from gupi.memory import Memory
    from gupi.records import Batch, Context, Referent, Source

    class Clock:
        now = datetime(2000, 1, 1, tzinfo=timezone.utc)

        def __call__(self):
            return self.now
    clock, db = Clock(), f"gupi-7b-harness-{uuid.uuid4().hex[:8]}"
    memory = Memory.open(db, packs=("core", "people"), driver=driver, create=True, clock=clock)
    try:
        authors = {(p["stated_author"], f"p:{_slug(p['stated_author'])}") for p in passages if p["stated_author"]}
        memory.ingest(Batch(referents=tuple(Referent(i, "person", n) for n, i in sorted(authors))))
        statuses = {}
        for p in sorted(passages, key=lambda p: (observation(p).observed_at, p["passage_id"])):
            obs, cset, _, _ = extracted[p["passage_id"]]
            clock.now = obs.observed_at
            memory.ingest(Batch((Source(obs.source_id, "corpus"),), (obs,), contexts=(Context(obs.context_id, "thread"),)))
            if cset.candidates:
                clock.now = obs.observed_at + timedelta(seconds=30)
                store.submit(memory, obs, cset)
                for c in cset.candidates:
                    s = store.get(memory, c.id)
                    statuses[c.id] = s.status if s else "not stored"
        return statuses
    finally:
        driver.databases.get(db).delete()


# --- matching -----------------------------------------------------------------------------------------

def norm(s):
    s = " ".join((s or "").casefold().split()).strip(" .,;:!?\"'")
    s = re.sub(r"^the ", "", s)
    return re.sub(r"'s$", "", s)


def _gold_groups(gold_rows):
    groups = {}
    for g in gold_rows:
        groups.setdefault(g["alternative_of"] or g["assertion_id"], []).append(g)
    return groups


def _gold_span(g, text):
    return ann.span_location(text, g["span_text"], g["span_occurrence"])


def _gold_roles(g):
    resolved = dict(ann.pairs(g["resolution"]))
    return {role: {norm(surface)} | ({norm(resolved[surface])} if resolved.get(surface, "?") != "?" else set())
            for role, surface in ann.pairs(g["participants"])}


def _tier(c, g, text):
    span = _gold_span(g, text)
    if not span or not (c.passage.start < span[1] and span[0] < c.passage.end) or c.claim_type != g["gupi_claim_type"]:
        return None
    want, got = _gold_roles(g), {p.role: norm(p.surface) for p in c.participants}
    same_roles = sum(1 for r, ok in want.items() if got.get(r) in ok)
    if same_roles == len(want) and set(got) == set(want):
        if c.claim_type == "statement":
            pred = dict(c.values).get("predicate-text", "")
            return "exact" if norm(pred) == norm(g["predicate"]) else "partial"
        return "exact"
    return "partial" if same_roles else None


def _overlaps(c, g, text):
    span = _gold_span(g, text)
    return bool(span and c.passage.start < span[1] and span[0] < c.passage.end)


# --- field scoring on a matched pair ------------------------------------------------------------------

def _date(t):
    return t.date().isoformat() if t else ""


def fields(c, g):
    times = [t for t in c.times if not (t.kind == "holds-at" and t.precision == "instant")]
    gold_expr = norm(g["time_expression"])
    out = {
        "attribution_mode": c.attribution.mode == g["attribution_mode"],
        "claimant": norm(c.attribution.asserted_by) == norm(g["original_claimant"]),
        "polarity": c.polarity == g["polarity"],
        "modality": c.modality == g["modality"],
        "commitment": c.commitment == g["commitment"],
    }
    if gold_expr or times:
        out["time_expression_preserved"] = bool(gold_expr) and any(
            norm(t.phrase) and (norm(t.phrase) in gold_expr or gold_expr in norm(t.phrase)) for t in times)
        out["time_kind"] = g["time_kind"] in {t.kind for t in times} if g["time_kind"] not in ("", "none") else not times
        same = [t for t in times if t.kind == g["time_kind"]]
        if same and (g["time_earliest"] or g["time_latest"]):
            t = same[0]
            out["time_window"] = ((t.kind == "holds-since" or _date(t.earliest) == g["time_earliest"])
                                  and _date(t.latest) == g["time_latest"])
    return out


def severe(c, g, status):
    """Evidence-integrity errors (success-criteria.md H1-H3) for a candidate matched (or partly) to gold."""
    errs = []
    if any(p.surface in PRONOUNS for p in c.participants):
        errs.append("pronoun admitted as a participant")
    want = set().union(*_gold_roles(g).values()) if _gold_roles(g) else set()
    if any(norm(p.surface) not in want for p in c.participants):
        errs.append("invented entity")
    if (c.commitment == "certain" and g["commitment"] != "certain") or \
            (c.attribution.mode == "direct" and g["attribution_mode"] in WEAKER_MODES):
        errs.append("unsupported certainty")
    if g["independent_origin"] == "no" and c.attribution.mode not in ("forwarded", "quoted") \
            and not any(r.kind == "repeats" for r in c.relations):
        errs.append("false independent corroboration")   # a copy presented as a first-hand attestation
    windowed = [t for t in c.times if t.earliest and not (t.kind == "holds-at" and t.precision == "instant")]
    if windowed and not (g["time_earliest"] or g["time_latest"]) and g["time_precision"] in ("approximate", "unknown",
                                                                                              "relative-unresolved"):
        errs.append("invented time")
    return errs


# --- scoring ---------------------------------------------------------------------------------------------

def wilson(k, n, z=1.96):
    if not n:
        return {"k": k, "n": n, "rate": None, "low": None, "high": None}
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return {"k": k, "n": n, "rate": round(p, 4), "low": round(max(0, c - h), 4), "high": round(min(1, c + h), 4)}


def score(passages, gold_rows, extracted, statuses=None):
    groups = _gold_groups(gold_rows)
    by_passage = {}
    for key, rows in groups.items():
        by_passage.setdefault(rows[0]["passage_id"], []).append(key)
    per_passage, adjudicate = [], []
    tally = {k: 0 for k in ("candidates", "matched", "partial", "duplicates", "unsupported", "abstained",
                            "abstained_appropriately", "validation_failures", "invalid_outputs", "grounding_failures",
                            "copies_formed")}
    fieldsum, severe_list, formation_counts, admission = {}, [], {}, {"agree": 0, "of": 0}
    representable = {"total": 0, "matched": 0}
    for p in passages:
        pid, text = p["passage_id"], p["text"]
        obs, cset, outcomes, flags = extracted[pid]
        keys = by_passage.get(pid, [])
        used, rows = set(), []
        tally["candidates"] += len(cset.candidates)
        for c in cset.candidates:
            best = None
            for key in keys:
                for g in groups[key]:
                    t = _tier(c, g, text)
                    if t == "exact" and (best is None or best[0] != "exact"):
                        best = (t, key, g)
                    elif t == "partial" and best is None:
                        best = (t, key, g)
            status = (statuses or {}).get(c.id)
            if status:
                formation_counts[status] = formation_counts.get(status, 0) + 1
            row = {"candidate": c.id, "type": c.claim_type, "participants": {x.role: x.surface for x in c.participants},
                   "evidence": c.passage.text, "status": status}
            if best and best[1] in used and best[0] == "exact":
                tally["duplicates"] += 1
                row["result"] = "duplicate"
            elif best and best[0] == "exact":
                used.add(best[1])
                tally["matched"] += 1
                f = fields(c, best[2])
                for k, ok in f.items():
                    fieldsum.setdefault(k, [0, 0])
                    fieldsum[k][0] += ok
                    fieldsum[k][1] += 1
                errs = severe(c, best[2], status)
                severe_list += [{"passage": pid, "candidate": c.id, "gold": best[2]["assertion_id"], "error": e} for e in errs]
                if status:
                    admission["of"] += 1
                    admission["agree"] += status == best[2]["expected_admission"]
                    if best[2]["independent_origin"] == "no" and status == "formed":
                        tally["copies_formed"] += 1   # a second claim for one attestation (not double-counted in answers)
                row.update(result="matched", gold=best[2]["assertion_id"], fields=f, severe=errs)
            elif best:
                tally["partial"] += 1
                errs = severe(c, best[2], status)
                severe_list += [{"passage": pid, "candidate": c.id, "gold": best[2]["assertion_id"], "error": e} for e in errs]
                row.update(result="partial", gold=best[2]["assertion_id"], severe=errs)
                adjudicate.append({"passage": pid, "candidate": c.id, "gold": best[2]["assertion_id"],
                                   "why": "partial match: same type, some participants differ"})
            elif any(_overlaps(c, g, text) for key in keys for g in groups[key]):
                row["result"] = "overlap, unmatched"
                adjudicate.append({"passage": pid, "candidate": c.id, "gold": [g["assertion_id"] for key in keys
                                                                               for g in groups[key] if _overlaps(c, g, text)],
                                   "why": "overlapping span, different reading: equivalent, partial or different?"})
            else:
                tally["unsupported"] += 1
                row["result"] = "unsupported (no gold assertion here)"
                severe_list.append({"passage": pid, "candidate": c.id, "gold": None,
                                    "error": "invented assertion" if not keys else "unsupported claim"})
            rows.append(row)
        missed = [k for k in keys if k not in used]
        for key in keys:
            g = groups[key][0]
            if g["gupi_claim_type"] != "none":
                representable["total"] += 1
                representable["matched"] += key in used
        for o in outcomes:
            tally["validation_failures"] += o["kind"] == "validation"
            tally["invalid_outputs"] += o["kind"] == "invalid-model-output"
            tally["grounding_failures"] += o["kind"] in ("grounding-failure", "ambiguous-span")
        for key in missed:
            g = groups[key][0]
            span = _gold_span(g, text)
            hit = [o for o in outcomes if o["evidence"] and span and _text_overlap(text, o["evidence"], span)]
            if hit:
                tally["abstained"] += 1
                if g["ambiguity"] or "?" in g["resolution"] or g["literal_or_inferred"] == "inferred" or g["representable"] != "yes":
                    tally["abstained_appropriately"] += 1
        per_passage.append({"passage": pid, "gold": [groups[k][0]["assertion_id"] for k in keys], "candidates": rows,
                            "missed": [groups[k][0]["assertion_id"] for k in missed], "outcomes": outcomes, "flags": flags})
    gold_total = sum(1 for g in groups.values() if g[0]["gupi_claim_type"] != "none")
    summary = {
        "precision": wilson(tally["matched"], tally["candidates"] - tally["duplicates"]),
        "recall": wilson(representable["matched"], gold_total),
        "f1": _f1(tally["matched"], tally["candidates"] - tally["duplicates"], representable["matched"], gold_total),
        "counts": tally, "fields": {k: wilson(a, b) for k, (a, b) in sorted(fieldsum.items())},
        "severe_errors": {"count": len(severe_list), "per_100_candidates": round(100 * len(severe_list) / tally["candidates"], 1)
                          if tally["candidates"] else None},
        "grounding_validity": wilson(tally["candidates"], tally["candidates"] + tally["grounding_failures"]),
        "formation": formation_counts or None,
        "formation_agrees_with_expected_admission": wilson(admission["agree"], admission["of"]) if statuses else None,
    }
    return {"summary": summary, "severe": severe_list, "adjudicate": adjudicate, "passages": per_passage}


def _text_overlap(text, evidence, span):
    i = text.find(evidence)
    return i != -1 and i < span[1] and span[0] < i + len(evidence)


def _f1(m, c, r, g):
    p, rec = (m / c if c else 0.0), (r / g if g else 0.0)
    return round(2 * p * rec / (p + rec), 4) if p + rec else 0.0


def run(folder, gold=None, responses=None, with_formation=False, driver=None):
    passages, gold_rows, recorded, hashes = load(folder, gold, responses)
    result = {"scorer": SCORER_VERSION, "parser": MODEL_METHOD, "response_format": RESPONSE_FORMAT, "files": hashes,
              "sets": sorted({p["set"] for p in passages}), "passages": len(passages), "gold_assertions": len(gold_rows),
              "formation": with_formation, "systems": {}}
    schema = None
    if with_formation:
        from gupi.typedb.connection import connect
        driver = driver or connect()
        result["typedb"] = driver.server_version().version
    for system in SYSTEMS:
        if system == MODEL_METHOD and not recorded:
            continue
        extracted = extract(passages, system, recorded, schema)
        statuses = formation(passages, extracted, driver) if with_formation else None
        result["systems"][system] = score(passages, gold_rows, extracted, statuses)
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("folder")
    p.add_argument("--gold")
    p.add_argument("--responses")
    p.add_argument("--formation", action="store_true", help="also run the candidate store (local TypeDB)")
    p.add_argument("--json")
    args = p.parse_args(argv)
    result = run(args.folder, args.gold, args.responses, args.formation)
    text = json.dumps(result, indent=1, default=str) + "\n"
    if args.json:
        Path(args.json).write_text(text)
    for system, r in result["systems"].items():
        s = r["summary"]
        print(f"{system:22} precision {s['precision']['k']}/{s['precision']['n']}  recall {s['recall']['k']}/{s['recall']['n']}  "
              f"F1 {s['f1']}  severe {s['severe_errors']['count']}  to adjudicate {len(r['adjudicate'])}  formation {s['formation']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
