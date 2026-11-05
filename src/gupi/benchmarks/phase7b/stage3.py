"""Phase 7B Stage 3: the blind extraction evaluation (docs/evaluation/phase-7b/stage-3/README.md).

    uv run python -I -m gupi.benchmarks.phase7b.stage3 check  --public <dir> [--private <dir>]
    uv run python -I -m gupi.benchmarks.phase7b.stage3 bundle --public <dir> --out <new dir>
    uv run python -I -m gupi.benchmarks.phase7b.stage3 score  --public <dir> --private <dir> [--responses <dir>]
        [--formation] --json <out>
    uv run python -I -m gupi.benchmarks.phase7b.stage3 audit  --transcripts <dir> --bundle <dir>

The public side (passages, the response format, the extraction instructions) is what an extraction session
may see. The private side (gold, annotation notes, passage categories) never enters the extraction bundle,
the repository or any git remote. Scoring needs both, plus the raw responses: one file per passage,
`<passage_id>.json`, kept exactly as the extractor wrote it. A missing or malformed file is scored as an
invalid output; nothing is ever regenerated or repaired.

Matching and the base metrics are the Phase 7B harness's (`phase7b-scorer/1`); this module adds the
evidence-integrity metrics, the pipeline outcomes and the severe-error definitions of the Stage 3 scoring
README, and keeps extraction, validation and formation results apart. Nothing here calls a model or the
network.
"""

import argparse
import hashlib
import json
import shutil
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from gupi.benchmarks.phase7b import annotations as ann
from gupi.benchmarks.phase7b import harness
from gupi.formation.model_candidate import METHOD as MODEL_METHOD, RESPONSE_FORMAT

SCORER_VERSION = "phase7b-stage3-scorer/1"
PASSAGE_FORMAT = "gupi.stage3-passages/1"
GOLD_FORMAT = "gupi.stage3-gold/1"
SET = "X3"
SYSTEMS = ("rules:v2.1", MODEL_METHOD)
PASSAGE_KEYS = {"passage_id", "thread_id", "turn", "document_kind", "stated_author", "document_date", "metadata",
                "text", "sha256"}
GOLD_KEYS = set(ann.ASSERTION_COLUMNS) | {"original_claimant_kind"}
CLAIMANT_KINDS = ("person", "organisation", "unknown")
CORRECTION_KINDS = ("corrects", "retracts", "updates", "contradicts")
BUNDLE_FILES = ("passages.jsonl", "response-format.md", "extraction-instructions.md", "README.md")
# what a Stage 3B extraction session may use; anything else in its transcripts invalidates the run
AUDIT_ALLOWED_TOOLS = {"Read", "Write", "Glob", "Grep", "TodoWrite"}

SEVERE = {
    "invented entity": "a participant not in the text, or not a referent of the gold assertion",
    "pronoun admitted as a participant": "a pronoun kept as a named participant",
    "invented assertion": "a candidate on a passage whose gold has no assertion",
    "unsupported claim": "a candidate that matches no gold assertion and overlaps none",
    "unsupported certainty": "certain or direct where gold is hedged, reported, rumour or allegation",
    "invented time": "a date window where gold justifies none",
    "false independent corroboration": "a repeat or forward presented as a first-hand attestation",
    "forwarded presented as first-hand": "gold forwarded, the candidate direct or reported",
    "invented claimant": "a claimant where gold has none (the author asserts it)",
    "misattributed claimant": "a claimant other than gold's original claimant",
    "invented claimant kind": "a person or organisation kind where gold says unknown, or the other kind",
    "guessed correction target": "a correction target where gold says the target is not established",
    "correction formed without review": "a correction, retraction or update formed automatically",
    "correction applied automatically": "a claim superseded during the run (nothing may supersede without review)",
    "inference formed": "a candidate formed automatically for an assertion gold marks inferred",
    "unsupported definitive assertion": "a certain claim formed automatically that matches no gold assertion exactly",
}


# --- files ------------------------------------------------------------------------------------------------

def read_jsonl(path):
    rows = []
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except ValueError as e:
                raise ValueError(f"{path} line {n}: not JSON ({e})") from None
    return rows


def text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_passages(passages):
    problems, seen = [], set()
    for n, p in enumerate(passages, 1):
        where = f"passage {p.get('passage_id') or n}"
        if set(p) != PASSAGE_KEYS:
            problems.append(f"{where}: keys must be exactly {sorted(PASSAGE_KEYS)}")
            continue
        if not p["passage_id"] or p["passage_id"] in seen:
            problems.append(f"{where}: passage_id empty or duplicated")
        seen.add(p["passage_id"])
        if not isinstance(p["text"], str) or not p["text"].strip():
            problems.append(f"{where}: text is empty")
        elif p["sha256"] != text_hash(p["text"]):
            problems.append(f"{where}: sha256 does not match the text")
        if (p["thread_id"] is None) != (p["turn"] is None):
            problems.append(f"{where}: thread_id and turn go together")
        if p["turn"] is not None and not (isinstance(p["turn"], int) and p["turn"] >= 1):
            problems.append(f"{where}: turn must be a positive integer")
        try:
            datetime.fromisoformat(p["document_date"])
        except (TypeError, ValueError):
            problems.append(f"{where}: document_date must be an ISO date")
        if not isinstance(p["metadata"], dict):
            problems.append(f"{where}: metadata must be an object (never part of the text)")
    return problems


def harness_rows(passages):
    """The Phase 7B harness's passage rows (annotations.PASSAGE_COLUMNS)."""
    return [{"passage_id": p["passage_id"], "set": SET, "thread_id": p["thread_id"] or "",
             "turn": str(p["turn"] or ""), "author_code": "", "document_kind": p["document_kind"],
             "stated_author": p["stated_author"] or "", "document_date": p["document_date"], "text": p["text"]}
            for p in passages]


def check_gold(gold, passages):
    problems = []
    for g in gold:
        if set(g) != GOLD_KEYS:
            problems.append(f"gold {g.get('assertion_id')}: keys must be the template's plus original_claimant_kind "
                            f"(missing {sorted(GOLD_KEYS - set(g))}, extra {sorted(set(g) - GOLD_KEYS)})")
    if problems:
        return problems
    rows = [{k: str(v) for k, v in g.items() if k != "original_claimant_kind"} for g in gold]
    problems += ann.check_assertions("gold.jsonl", list(ann.ASSERTION_COLUMNS), rows,
                                     {p["passage_id"]: p for p in harness_rows(passages)})
    for g in gold:
        kind, claimant = g["original_claimant_kind"], g["original_claimant"]
        if claimant and kind not in CLAIMANT_KINDS:
            problems.append(f"gold {g['assertion_id']}: a claimant needs original_claimant_kind in {CLAIMANT_KINDS}")
        if not claimant and kind:
            problems.append(f"gold {g['assertion_id']}: original_claimant_kind without an original_claimant")
    return problems


def load(public, private=None):
    public = Path(public)
    passages = read_jsonl(public / "passages.jsonl")
    problems = check_passages(passages)
    gold, categories = [], {}
    if private:
        private = Path(private)
        gold = read_jsonl(private / "gold.jsonl")
        categories = json.loads((private / "categories.json").read_text())
        problems += check_gold(gold, passages)
        problems += [f"categories: unknown passage {k}" for k in categories if k not in {p["passage_id"] for p in passages}]
        problems += [f"categories: no category for {p['passage_id']}" for p in passages if p["passage_id"] not in categories]
        problems += [f"categories: {k} needs primary, categories and negative_control" for k, v in categories.items()
                     if set(v) != {"primary", "categories", "negative_control"}]
    if problems:
        raise ValueError("the evaluation fails the structural check:\n" + "\n".join(problems))
    return passages, gold, categories


def read_responses(folder, passages):
    """{passage id: raw text, or None when no file was written}, and the hash of each file found."""
    folder = Path(folder)
    raw, hashes = {}, {}
    for p in passages:
        f = folder / f"{p['passage_id']}.json"
        raw[p["passage_id"]] = f.read_text(encoding="utf-8") if f.exists() else None
        if f.exists():
            hashes[f.name] = file_hash(f)
    extra = sorted(f.name for f in folder.glob("*.json") if f.stem not in raw)
    return raw, hashes, extra


# --- formation (a disposable local database) --------------------------------------------------------

def formation(rows, extracted, driver):
    """Every candidate through store.submit. Returns statuses, decision reasons, store-level validator
    rejections, formation failures (exceptions) and the number of supersessions recorded (which must be 0)."""
    from gupi.formation import store
    from gupi.memory import Memory
    from gupi.records import Batch, Context, Referent, Source

    class Clock:
        now = datetime(2000, 1, 1, tzinfo=timezone.utc)

        def __call__(self):
            return self.now
    clock, db = Clock(), f"gupi-stage3-{uuid.uuid4().hex[:8]}"
    memory = Memory.open(db, packs=("core", "people"), driver=driver, create=True, clock=clock)
    out = {"statuses": {}, "reasons": {}, "store_invalid": [], "failures": [], "superseded": 0}
    try:
        authors = {(p["stated_author"], f"p:{harness._slug(p['stated_author'])}") for p in rows if p["stated_author"]}
        memory.ingest(Batch(referents=tuple(Referent(i, "person", n) for n, i in sorted(authors))))
        for p in sorted(rows, key=lambda p: (harness.observation(p).observed_at, p["passage_id"])):
            obs, cset, _, _ = extracted[p["passage_id"]]
            clock.now = obs.observed_at
            memory.ingest(Batch((Source(obs.source_id, "corpus"),), (obs,), contexts=(Context(obs.context_id, "thread"),)))
            if not cset.candidates:
                continue
            clock.now = obs.observed_at + timedelta(seconds=30)
            try:
                result = store.submit(memory, obs, cset)
            except Exception as e:  # recorded, never hidden: a formation failure is its own category
                out["failures"].append({"passage": p["passage_id"], "error": f"{type(e).__name__}: {e}"})
                continue
            for n, why in result.invalid:
                cid = cset.candidates[n].id if n is not None else None
                out["store_invalid"].append({"passage": p["passage_id"], "candidate": cid, "reason": why})
            for c in cset.candidates:
                s = store.get(memory, c.id)
                if s is not None:
                    out["statuses"][c.id] = s.status
                    out["reasons"][c.id] = s.decisions[-1].reason if s.decisions else ""
        out["superseded"] = sum(1 for c in memory.all_claims() if c.superseded_by)
        return out
    finally:
        driver.databases.get(db).delete()


# --- scoring ---------------------------------------------------------------------------------------------

def _rate(pairs):
    return harness.wilson(sum(1 for ok in pairs if ok), len(pairs))


def evaluate(passages, gold, extracted, categories=None, formed=None):
    """Score one system. `extracted` is harness.extract's output; `formed` is formation()'s, or None."""
    formed = formed or {}
    statuses, reasons = formed.get("statuses"), formed.get("reasons", {})
    rows = harness_rows(passages)
    gold_rows = [{k: str(v) for k, v in g.items()} for g in gold]
    base = harness.score(rows, gold_rows, extracted, statuses)
    by_gold = {g["assertion_id"]: g for g in gold_rows}
    cands = {c.id: c for _, cset, _, _ in extracted.values() for c in cset.candidates}
    matched = [(cands[r["candidate"]], by_gold[r["gold"]], dict(r, passage=p["passage"])) for p in base["passages"]
               for r in p["candidates"] if r["result"] == "matched"]
    gold_to_candidate = {g["assertion_id"]: c.id for c, g, _ in matched}

    integrity = {k: [] for k in ("claimant", "claimant_kind", "attribution_mode", "forwarding_origin",
                                 "independent_corroboration", "temporal", "correction_detected", "correction_kind",
                                 "correction_target", "uncertainty_preserved", "commitment")}
    severe = list(base["severe"])
    for c, g, r in matched:
        kind_gold = g["original_claimant_kind"] or None
        kind_got = c.attribution.asserted_by_kind
        integrity["claimant"].append(r["fields"]["claimant"])
        integrity["attribution_mode"].append(r["fields"]["attribution_mode"])
        integrity["commitment"].append(r["fields"]["commitment"])
        if g["original_claimant"] or c.attribution.asserted_by:
            integrity["claimant_kind"].append((kind_got or None) == kind_gold)
        if g["attribution_mode"] == "forwarded":
            integrity["forwarding_origin"].append(c.attribution.mode == "forwarded"
                                                  and harness.norm(c.attribution.asserted_by) == harness.norm(g["original_claimant"]))
        if g["commitment"] != "certain":
            integrity["uncertainty_preserved"].append(c.commitment != "certain")
        time_fields = [v for k, v in r["fields"].items() if k.startswith("time")]
        if time_fields:
            integrity["temporal"].append(all(time_fields))
        status = r.get("status")
        if statuses is not None and status:
            copy = status == "withheld" and "repeats" in reasons.get(c.id, "")
            integrity["independent_corroboration"].append(copy if g["independent_origin"] == "no" else not copy)
        rel = next((x for x in c.relations if x.kind in CORRECTION_KINDS), None)
        if g["relation_to_earlier"] in CORRECTION_KINDS:
            integrity["correction_detected"].append(rel is not None)
            if rel is not None:
                integrity["correction_kind"].append(rel.kind == g["relation_to_earlier"])
                want = None if g["target_assertion_id"] == "?" else gold_to_candidate.get(g["target_assertion_id"], "unmatched")
                integrity["correction_target"].append(rel.target == want)
                if g["target_assertion_id"] == "?" and rel.target is not None:
                    severe.append(_err(r, c, g, "guessed correction target"))
        # Stage 3 severe errors on matched pairs (the harness's own are already in base["severe"])
        if c.attribution.asserted_by and not g["original_claimant"]:
            severe.append(_err(r, c, g, "invented claimant"))
        elif c.attribution.asserted_by and harness.norm(c.attribution.asserted_by) != harness.norm(g["original_claimant"]):
            severe.append(_err(r, c, g, "misattributed claimant"))
        if kind_got in ("person", "organisation") and kind_got != kind_gold:
            severe.append(_err(r, c, g, "invented claimant kind"))
        if g["attribution_mode"] == "forwarded" and c.attribution.mode in ("direct", "reported"):
            severe.append(_err(r, c, g, "forwarded presented as first-hand"))
        if status == "formed" and rel is not None and rel.kind in ("corrects", "retracts", "updates"):
            severe.append(_err(r, c, g, "correction formed without review"))
        if status == "formed" and g["literal_or_inferred"] == "inferred":
            severe.append(_err(r, c, g, "inference formed"))
    if formed.get("superseded"):
        severe.append({"passage": None, "candidate": None, "gold": None, "error": "correction applied automatically",
                       "detail": f"{formed['superseded']} supersession(s) recorded during the run"})
    gold_by_id = {g["assertion_id"]: g for g in gold_rows}
    disagreements = []
    for p in base["passages"]:
        for r in p["candidates"]:
            c = cands[r["candidate"]]
            g = gold_by_id.get(r.get("gold")) if r["result"] == "matched" else None
            if g is not None and r.get("status") and r["status"] != g["expected_admission"]:
                # a pipeline outcome, kept apart from extraction errors: the extraction matched the gold
                disagreements.append({"passage": p["passage"], "candidate": c.id, "gold": g["assertion_id"],
                                      "status": r["status"], "expected": g["expected_admission"]})
            if r.get("status") == "formed" and c.commitment == "certain" and g is None:
                severe.append(_err(dict(r, passage=p["passage"]), c, None, "unsupported definitive assertion"))
    for e in severe:
        e.setdefault("status", (statuses or {}).get(e["candidate"]))

    outcomes, flags = {}, {}
    for _, _, out, fl in extracted.values():
        for o in out:
            outcomes[o["kind"]] = outcomes.get(o["kind"], 0) + 1
        for f in fl:
            flags[f["kind"]] = flags.get(f["kind"], 0) + 1
    validation = outcomes.pop("validation", 0)
    pipeline = {
        "extraction_outcomes": dict(sorted(outcomes.items())),
        "extraction_flags": dict(sorted(flags.items())),
        "candidates": base["summary"]["counts"]["candidates"],
        "validator_rejections": {"extractor": validation, "store": len(formed.get("store_invalid", []))},
        "formation": None if statuses is None else {
            k: sum(1 for s in statuses.values() if s == k) for k in ("formed", "review", "withheld", "rejected")},
        "formation_failures": formed.get("failures", []),
        "admission_disagreements": disagreements if statuses is not None else None,
        "duplicate_original_attestations": base["summary"]["counts"]["copies_formed"]
            + sum(1 for p in base["passages"] for r in p["candidates"] if r["result"] == "duplicate" and r.get("status") == "formed"),
        "supersessions_during_run": formed.get("superseded", 0) if statuses is not None else None,
    }
    by_kind = {}
    for e in severe:
        by_kind[e["error"]] = by_kind.get(e["error"], 0) + 1
    result = {
        "summary": base["summary"],
        "integrity": {k: _rate(v) for k, v in integrity.items()},
        "pipeline": pipeline,
        "severe_errors": {"count": len(severe), "by_kind": dict(sorted(by_kind.items())),
                          "formed": sum(1 for e in severe if e.get("status") == "formed"), "list": severe},
        "by_category": _by_category(base, gold_rows, categories or {}),
        "adjudicate": base["adjudicate"],
        "passages": base["passages"],
    }
    return result


def _err(r, c, g, kind):
    return {"passage": r.get("passage"), "candidate": c.id,
            "gold": g["assertion_id"] if g else None, "error": kind, "status": r.get("status")}


def _by_category(base, gold_rows, categories):
    """Recall per declared passage category (a passage may have several)."""
    out = {}
    for p in base["passages"]:
        for cat in categories.get(p["passage"], {}).get("categories", []):
            o = out.setdefault(cat, {"passages": 0, "gold": 0, "matched": 0})
            o["passages"] += 1
            o["gold"] += len(p["gold"])
            o["matched"] += len(p["gold"]) - len(p["missed"])
    return dict(sorted(out.items()))


def run(public, private, responses=None, with_formation=False, driver=None, systems=SYSTEMS):
    passages, gold, categories = load(public, private)
    rows = harness_rows(passages)
    raw, response_hashes, extra = read_responses(responses, passages) if responses else ({}, {}, [])
    result = {"scorer": SCORER_VERSION, "base_scorer": harness.SCORER_VERSION, "parser": MODEL_METHOD,
              "response_format": RESPONSE_FORMAT, "passages": len(passages), "gold_assertions": len(gold),
              "files": {"passages.jsonl": file_hash(Path(public) / "passages.jsonl"),
                        "gold.jsonl": file_hash(Path(private) / "gold.jsonl"),
                        "categories.json": file_hash(Path(private) / "categories.json")},
              "responses": {"files": response_hashes, "missing": sorted(k for k, v in raw.items() if v is None),
                            "unexpected": extra} if responses else None,
              "formation": with_formation, "systems": {}}
    if with_formation:
        from gupi.typedb.connection import connect
        driver = driver or connect()
        result["typedb"] = driver.server_version().version
    for system in systems:
        if system == MODEL_METHOD and not responses:
            continue
        extracted = harness.extract(rows, system, raw)
        formed = formation(rows, extracted, driver) if with_formation else None
        result["systems"][system] = evaluate(passages, gold, extracted, categories, formed)
    return result


# --- the extraction bundle and its audit --------------------------------------------------------------

def bundle(public, out):
    """Copy the public files, and only those, into a new directory for an extraction session."""
    public, out = Path(public), Path(out)
    if out.exists():
        raise FileExistsError(f"{out} exists: a bundle is written once, into a new directory")
    passages = read_jsonl(public / "passages.jsonl")
    if problems := check_passages(passages):
        raise ValueError("\n".join(problems))
    out.mkdir(parents=True)
    for name in BUNDLE_FILES:
        shutil.copyfile(public / name, out / name)
    (out / "responses").mkdir()
    (out / ".claude").mkdir()
    shutil.copyfile(public / "claude-settings.json", out / ".claude" / "settings.json")
    return {name: file_hash(out / name) for name in BUNDLE_FILES} | {".claude/settings.json": file_hash(out / ".claude" / "settings.json")}


def audit(transcripts, bundle_dir):
    """Every tool call in an extraction session's transcripts (JSONL files, subagents included): a call to a
    tool outside AUDIT_ALLOWED_TOOLS, a path outside the bundle, or a response written more than once (a
    regenerated output) makes the run invalid."""
    bundle_dir = str(Path(bundle_dir).resolve())
    calls, violations, files, written = [], [], sorted(Path(transcripts).rglob("*.jsonl")), {}
    for f in files:
        for line in f.read_text(encoding="utf-8").splitlines():
            try:
                d = json.loads(line)
            except ValueError:
                violations.append({"file": f.name, "problem": "unreadable transcript line"})
                continue
            content = (d.get("message") or {}).get("content")
            for block in content if isinstance(content, list) else []:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                name, inp = block.get("name"), block.get("input") or {}
                calls.append(name)
                if name not in AUDIT_ALLOWED_TOOLS:
                    violations.append({"file": f.name, "tool": name, "problem": "tool not allowed"})
                for key in ("file_path", "path", "notebook_path"):
                    if key in inp and not str(Path(inp[key]).resolve()).startswith(bundle_dir):
                        violations.append({"file": f.name, "tool": name, "path": inp[key], "problem": "outside the bundle"})
                if name == "Glob" and str(inp.get("pattern", "")).startswith(("/", "~", "..")):
                    violations.append({"file": f.name, "tool": name, "pattern": inp["pattern"], "problem": "outside the bundle"})
                if name == "Write" and "file_path" in inp:
                    target = str(Path(inp["file_path"]).resolve())
                    written[target] = written.get(target, 0) + 1
                    if written[target] == 2:
                        violations.append({"file": f.name, "tool": name, "path": inp["file_path"], "problem": "response rewritten"})
    counts = {}
    for c in calls:
        counts[c] = counts.get(c, 0) + 1
    return {"transcript_files": len(files), "tool_calls": dict(sorted(counts.items())), "violations": violations,
            "valid": bool(files) and not violations}


CODE = ("src/gupi/benchmarks/phase7b/stage3.py", "src/gupi/benchmarks/phase7b/harness.py",
        "src/gupi/benchmarks/phase7b/annotations.py", "src/gupi/formation/model_candidate.py",
        "src/gupi/formation/candidate.py", "src/gupi/formation/validate.py", "src/gupi/formation/form.py",
        "src/gupi/formation/fidelity.py", "src/gupi/formation/store.py", "src/gupi/formation/rules_v21.py", "src/gupi/formation/rules_v2.py",
        "src/gupi/timeexpr.py")
EXTRACTION_CONTRACT = "gupi.stage3-extraction/1"


def manifest(public, private, bundle_dir, out, repo, typedb_version=None):
    """The Stage 3A freeze record: hashes only, never gold content. Refuses to overwrite."""
    import platform
    import subprocess
    from importlib.metadata import version

    from gupi.formation.candidate import IR_VERSION_1_1
    out, public, private, bundle_dir, repo = map(Path, (out, public, private, bundle_dir, repo))
    if out.exists():
        raise FileExistsError(f"{out} exists: a manifest is written once; a new freeze is a new version")
    passages, gold, categories = load(public, private)

    def git(folder, *args):
        return subprocess.run(["git", "-C", str(folder), *args], capture_output=True, text=True, check=True).stdout.strip()
    record = {
        "manifest": "gupi.stage3a-manifest/1",
        "created": datetime.now(timezone.utc).date().isoformat(),
        "repository": {"commit": git(repo, "rev-parse", "HEAD"), "branch": git(repo, "branch", "--show-current"),
                       "clean": git(repo, "status", "--porcelain") == ""},
        "environment": {"python": platform.python_version(), "platform": platform.system() + " " + platform.machine(),
                        "typedb": typedb_version, "typedb_driver": version("typedb-driver")},
        "formats": {"candidate": IR_VERSION_1_1, "response": RESPONSE_FORMAT, "parser": MODEL_METHOD,
                    "extraction_contract": EXTRACTION_CONTRACT, "passages": PASSAGE_FORMAT, "gold": GOLD_FORMAT},
        "passages": {"count": len(passages), "file_sha256": file_hash(public / "passages.jsonl"),
                     "items": [{"passage_id": p["passage_id"], "text_sha256": p["sha256"]} for p in passages]},
        "public_files": {name: file_hash(public / name) for name in BUNDLE_FILES + ("claude-settings.json",)},
        "bundle": {"files": {name: file_hash(bundle_dir / name) for name in BUNDLE_FILES}
                   | {".claude/settings.json": file_hash(bundle_dir / ".claude" / "settings.json")},
                   "commit": git(bundle_dir, "rev-parse", "HEAD"), "remotes": git(bundle_dir, "remote") or None},
        "gold": {"version": "v1", "assertions": len(gold), "gold_sha256": file_hash(private / "gold.jsonl"),
                 "categories_sha256": file_hash(private / "categories.json"),
                 "annotation_notes_sha256": file_hash(private / "annotation-notes.md"),
                 "private_commit": git(private, "rev-parse", "HEAD"), "private_remotes": git(private, "remote") or None,
                 "provenance": "developer-authored (Claude, Stage 3A session); not independently annotated"},
        "scoring": {"scorer": SCORER_VERSION, "base_scorer": harness.SCORER_VERSION,
                    "code_sha256": {f: file_hash(repo / f) for f in CODE}},
        "baseline": {"extractor": "rules:v2.1", "unchanged_for_this_corpus": True},
        "categories": {k: sum(1 for v in categories.values() if v["primary"] == k)
                       for k in sorted({v["primary"] for v in categories.values()})},
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=1) + "\n")
    return record


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("command", choices=("check", "bundle", "score", "audit", "manifest"))
    p.add_argument("--public")
    p.add_argument("--private")
    p.add_argument("--responses")
    p.add_argument("--out")
    p.add_argument("--formation", action="store_true")
    p.add_argument("--json")
    p.add_argument("--transcripts")
    p.add_argument("--bundle")
    p.add_argument("--typedb")
    args = p.parse_args(argv)
    if args.command == "manifest":
        r = manifest(args.public, args.private, args.bundle, args.out, Path.cwd(), args.typedb)
        print(json.dumps({k: r[k] for k in ("repository", "formats", "gold")}, indent=1))
        return 0
    if args.command == "check":
        passages, gold, categories = load(args.public, args.private)
        print(json.dumps({"passages": len(passages), "gold_assertions": len(gold), "categorised": len(categories),
                          "problems": 0}))
        return 0
    if args.command == "bundle":
        print(json.dumps(bundle(args.public, args.out), indent=1))
        return 0
    if args.command == "audit":
        r = audit(args.transcripts, args.bundle)
        print(json.dumps(r, indent=1))
        return 0 if r["valid"] else 1
    result = run(args.public, args.private, args.responses, args.formation)
    Path(args.json).write_text(json.dumps(result, indent=1, default=str) + "\n")
    for system, r in result["systems"].items():
        s = r["summary"]
        print(f"{system:22} precision {s['precision']['k']}/{s['precision']['n']}  recall {s['recall']['k']}/{s['recall']['n']}  "
              f"severe {r['severe_errors']['count']}  formation {r['pipeline']['formation']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
