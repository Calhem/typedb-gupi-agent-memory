"""Structural checks for Phase 7B gold annotations (docs/evaluation/phase-7b/annotation-guidelines.md).

    uv run python -I -m gupi.benchmarks.phase7b.annotations check <folder>
    uv run python -I -m gupi.benchmarks.phase7b.annotations compare <assertions-A.csv> <assertions-B.csv> <passages.csv>

`check` verifies structure only: required columns, allowed values, that every span, participant surface,
claimant and time expression occurs in its passage, and that ids and targets exist. It never judges whether
an annotation is right. `compare` pairs two annotators' assertions (same passage, overlapping spans) and lists
the fields that differ, and assertions only one annotator found, for adjudication. Evaluation tooling only.
"""

import csv
import sys
from pathlib import Path

PASSAGE_COLUMNS = ["passage_id", "set", "thread_id", "turn", "author_code", "document_kind", "stated_author",
                   "document_date", "text"]
ASSERTION_COLUMNS = [
    "assertion_id", "passage_id", "span_text", "span_occurrence", "relation", "gupi_claim_type", "participants",
    "resolution", "predicate", "title", "source_speaker", "original_claimant", "attribution_chain",
    "attribution_mode", "independent_origin", "polarity", "modality", "commitment", "allegation",
    "time_expression", "time_kind", "time_earliest", "time_latest", "time_precision", "time_basis",
    "relation_to_earlier", "target_assertion_id", "literal_or_inferred", "representable", "representation_gap",
    "expected_admission", "ambiguity", "alternative_of", "notes"]
ENUMS = {
    "gupi_claim_type": {"employment", "reporting", "statement", "none"},
    "attribution_mode": {"direct", "reported", "quoted", "forwarded", "rumour", "unattributed"},
    "independent_origin": {"yes", "no", "unclear"},
    "polarity": {"positive", "negative"},
    "modality": {"actual", "planned", "required", "permitted", "requested", "conditional", "hypothetical", "question"},
    "commitment": {"certain", "probable", "possible", "unknown"},
    "allegation": {"yes", "no"},
    "time_kind": {"start", "end", "holds-since", "holds-at", "none", ""},
    "time_precision": {"day", "month", "year", "approximate", "relative-unresolved", "unknown", ""},
    "time_basis": {"stated", "document-date", "tense-only", "none", ""},
    "relation_to_earlier": {"corrects", "retracts", "updates", "repeats", "contradicts", "none"},
    "literal_or_inferred": {"literal", "inferred"},
    "representable": {"yes", "partial", "no"},
    "expected_admission": {"formed", "review", "withheld", "not-extractable"},
}
SETS = {"S1", "S2", "DEV"}
COMPARED = [c for c in ASSERTION_COLUMNS if c not in ("assertion_id", "notes", "span_occurrence")]


def read(path):
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        return list(r.fieldnames or []), [{k: (v or "").strip() if k != "text" else (v or "") for k, v in row.items()}
                                          for row in r]


def pairs(field):
    """'role=surface | role=surface' -> [(role, surface)]."""
    out = []
    for part in [p.strip() for p in field.split("|") if p.strip()]:
        role, _, surface = part.partition("=")
        out.append((role.strip(), surface.strip()))
    return out


def span_location(text, span, occurrence):
    """(start, end) of the requested occurrence, or None. Exact, case-sensitive."""
    if not span:
        return None
    starts, i = [], text.find(span)
    while i != -1:
        starts.append(i)
        i = text.find(span, i + 1)
    n = int(occurrence) if occurrence.isdigit() else 1
    if not starts or n < 1 or n > len(starts):
        return None
    return starts[n - 1], starts[n - 1] + len(span)


def check_passages(columns, rows):
    problems = []
    if columns != PASSAGE_COLUMNS:
        problems.append(f"passages.csv columns must be exactly {PASSAGE_COLUMNS}")
    seen = set()
    for n, r in enumerate(rows, 2):
        if not r.get("passage_id"):
            problems.append(f"passages.csv line {n}: passage_id is empty")
        elif r["passage_id"] in seen:
            problems.append(f"passages.csv line {n}: duplicate passage_id {r['passage_id']}")
        seen.add(r.get("passage_id"))
        if r.get("set") not in SETS:
            problems.append(f"passages.csv line {n}: set must be one of {sorted(SETS)}")
        if not r.get("text", "").strip():
            problems.append(f"passages.csv line {n}: text is empty")
        if r.get("set") == "S2" and not (r.get("thread_id") and r.get("turn", "").isdigit() and r.get("stated_author")):
            problems.append(f"passages.csv line {n}: S2 turns need thread_id, a numeric turn and stated_author")
    return problems


def check_assertions(name, columns, rows, passages):
    problems = []
    if columns != ASSERTION_COLUMNS:
        problems.append(f"{name}: columns must be exactly the template's ({len(ASSERTION_COLUMNS)} columns)")
        return problems
    ids = [r["assertion_id"] for r in rows]
    for dup in sorted({i for i in ids if ids.count(i) > 1}):
        problems.append(f"{name}: duplicate assertion_id {dup}")
    for r in rows:
        where = f"{name} {r['assertion_id'] or '(no id)'}"
        p = passages.get(r["passage_id"])
        if p is None:
            problems.append(f"{where}: unknown passage_id {r['passage_id']!r}")
            continue
        text = p["text"]
        for field, allowed in ENUMS.items():
            if r[field] not in allowed:
                problems.append(f"{where}: {field} {r[field]!r} is not one of {sorted(a for a in allowed if a)}")
        loc = span_location(text, r["span_text"], r["span_occurrence"])
        if loc is None:
            problems.append(f"{where}: span_text does not occur in the passage (occurrence {r['span_occurrence'] or 1})")
        elif text.count(r["span_text"]) > 1 and not r["span_occurrence"]:
            problems.append(f"{where}: span_text occurs {text.count(r['span_text'])} times; set span_occurrence")
        roles = pairs(r["participants"])
        if r["gupi_claim_type"] != "none" and not roles:
            problems.append(f"{where}: participants are required unless gupi_claim_type is none")
        for role, surface in roles:
            if not role or not surface:
                problems.append(f"{where}: participants must be role=surface pairs")
            elif surface not in text:
                problems.append(f"{where}: participant {surface!r} does not occur in the passage")
        for surface, antecedent in pairs(r["resolution"]):
            if antecedent != "?" and antecedent not in text:
                problems.append(f"{where}: resolution antecedent {antecedent!r} does not occur in the passage")
        for field in ("original_claimant", "time_expression", "title"):
            if r[field] and r[field] not in text:
                problems.append(f"{where}: {field} {r[field]!r} does not occur in the passage")
        if r["time_expression"] and not r["time_kind"]:
            problems.append(f"{where}: a time_expression needs a time_kind")
        if r["relation_to_earlier"] != "none" and not r["target_assertion_id"]:
            problems.append(f"{where}: relation_to_earlier needs target_assertion_id (or '?')")
        if r["representable"] != "yes" and not r["representation_gap"]:
            problems.append(f"{where}: representable {r['representable']} needs a representation_gap")
        if r["ambiguity"] == "" and r["alternative_of"]:
            problems.append(f"{where}: alternative_of needs an ambiguity description")
    known = set(ids)
    for r in rows:
        for field in ("target_assertion_id", "alternative_of"):
            if r[field] and r[field] != "?" and r[field] not in known:
                problems.append(f"{name} {r['assertion_id']}: {field} {r[field]!r} is not an assertion_id in this file")
    return problems


def check(folder):
    folder = Path(folder)
    columns, rows = read(folder / "passages.csv")
    problems = check_passages(columns, rows)
    passages = {r["passage_id"]: r for r in rows}
    files = sorted(folder.glob("assertions*.csv"))
    if not files:
        problems.append("no assertions*.csv file")
    for f in files:
        c, a = read(f)
        problems += check_assertions(f.name, c, a, passages)
    return problems


def _overlap(a, b, text):
    la, lb = span_location(text, a["span_text"], a["span_occurrence"]), span_location(text, b["span_text"], b["span_occurrence"])
    return bool(la and lb and la[0] < lb[1] and lb[0] < la[1])


def compare(path_a, path_b, passages_path):
    """Disagreements between two annotators' files, for adjudication."""
    _, pa = read(passages_path)
    passages = {r["passage_id"]: r["text"] for r in pa}
    (_, a), (_, b) = read(path_a), read(path_b)
    free_b, rows = list(b), []
    for x in a:
        same = [y for y in free_b if y["passage_id"] == x["passage_id"] and y["gupi_claim_type"] == x["gupi_claim_type"]
                and _overlap(x, y, passages.get(x["passage_id"], ""))]
        if not same:
            rows.append({"item": x["assertion_id"], "passage_id": x["passage_id"], "field": "(only in A)"})
            continue
        y = same[0]
        free_b.remove(y)
        for field in COMPARED:
            if x[field] != y[field]:
                rows.append({"item": f"{x['assertion_id']}~{y['assertion_id']}", "passage_id": x["passage_id"],
                             "field": field, "annotator_a": x[field], "annotator_b": y[field]})
    rows += [{"item": y["assertion_id"], "passage_id": y["passage_id"], "field": "(only in B)"} for y in free_b]
    return rows


def main(argv=None):
    args = argv or sys.argv[1:]
    if args[:1] == ["check"] and len(args) == 2:
        problems = check(args[1])
        print("\n".join(problems) if problems else "no structural problems")
        return 1 if problems else 0
    if args[:1] == ["compare"] and len(args) == 4:
        rows = compare(*args[1:])
        w = csv.DictWriter(sys.stdout, fieldnames=["item", "passage_id", "field", "annotator_a", "annotator_b"])
        w.writeheader()
        w.writerows(rows)
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
