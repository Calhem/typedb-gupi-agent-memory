"""Export spreadsheet annotations to the canonical JSON Lines format, and read them back.

    python -I scripts/annotation_export.py SHEETS_DIR OUT_DIR --annotator NAME

SHEETS_DIR holds the CSV sheets of docs/specialist/authoring-trial/annotation-template; the rules are the
template README's, applied mechanically: nothing is guessed, and every problem is reported. Evaluation
tooling only (standard library; not part of the `gupi` package).
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

RECORDS = {  # sheet -> record name, in output order
    "documents": "document", "segments": "segment", "entities": "entity", "mentions": "mention", "times": "time",
    "statements": "statement", "links": "link", "judgements": "judgement", "questions": "question",
    "answers": "answer", "adjudication": "adjudication",
}
CHILDREN = ("participants", "answer_evidence", "answer_sides", "answer_alternatives", "rejected_candidates")
SHEETS = tuple(RECORDS) + CHILDREN
LISTS = {"aliases", "holds_at", "via", "based_on", "against", "inference", "value_forms", "items", "statements"}
INTS = {"start", "end", "set", "alt"}
CONFIDENCE = {"high", "medium", "low"}
INFERENCES = {"continuation", "combination", "date-calculation", "reference", "consequence", "closed-list", "other"}
STATUSES = {"stated", "inferred", "disputed", "insufficient", "not-yet-available"}
ENUMS = {
    ("documents", "kind"): None,
    ("segments", "relation"): {"original", "reply-to", "quote-of", "forward-of"},
    ("mentions", "reference"): {"name", "pronoun", "role-reference", "description"},
    ("mentions", "resolved"): {"stated", "inferred", "unresolved"},
    ("times", "granularity"): {"day", "week", "month", "quarter", "year", "other"},
    ("times", "anchor"): {"explicit", "document-date", "other-time", "inferred", "unresolvable"},
    ("statements", "kind"): {"state", "event", "decision", "obligation", "other"},
    ("statements", "polarity"): {"affirmed", "negated"},
    ("statements", "conveyed"): {"stated", "implied"},
    ("statements", "commitment"): {"certain", "probable", "possible", "unknown"},
    ("statements", "modality"): {"actual", "planned", "required", "permitted", "requested", "conditional",
                                 "hypothetical", "question"},
    ("statements", "attribution"): {"direct", "reported", "quoted", "forwarded", "rumour", "unattributed"},
    ("statements", "standing"): {"authoritative-record", "direct-observation", "reported", "plan", "unverified"},
    ("participants", "filler_kind"): {"entity", "time", "value", "statement"},
    ("links", "type"): {"corroborates", "contradicts", "corrects", "retracts", "updates", "refines", "repeats",
                        "resumes", "fulfils", "cancels", "depends-on", "doubts"},
    ("links", "marked"): {"stated", "inferred"},
    ("judgements", "kind"): {"state", "event", "decision", "obligation", "other"},
    ("judgements", "belief"): {"happened", "did-not-happen", "uncertain", "sources-disagree"},
    ("judgements", "reasoning"): {"taken-from-source", "inferred"},
    ("questions", "answer_type"): {"yes-no", "entity", "list", "date", "value", "short-text"},
    ("questions", "mode"): {"at", "throughout", "at-some-time"},
    ("questions", "frame"): {"recorded", "actual", "unspecified"},
    ("answers", "frame"): {"recorded", "actual"},
    ("answers", "status"): STATUSES,
    ("answers", "ambiguity"): {"none", "wording", "evidence", "frame"},
    ("answer_evidence", "kind"): {"essential", "context", "counter"},
    ("answer_alternatives", "status"): STATUSES,
    ("rejected_candidates", "reason"): {"rumour-only", "hedged-only", "corrected", "retracted", "updated", "plan-only",
                                        "outside-time-asked", "not-available-by-as-of", "wrong-reference", "other"},
    ("adjudication", "outcome"): {"a-correct", "b-correct", "both-acceptable", "merged", "unresolvable"},
    ("adjudication", "cause"): {"guideline unclear", "guideline silent", "document ambiguous", "annotator slip",
                                "genuine disagreement"},
}
REQUIRED = {
    "documents": ("id", "kind", "file"), "segments": ("id", "document", "start", "end", "author", "written"),
    "entities": ("id", "kind", "name"), "mentions": ("id", "segment", "start", "end", "text", "reference", "resolved"),
    "times": ("id", "segment", "text", "granularity", "anchor"),
    "statements": ("id", "segment", "spans", "kind", "description", "polarity", "conveyed", "commitment", "modality",
                   "asserted_by", "attribution", "standing", "standing_reason"),
    "participants": ("owner", "role", "filler_kind", "filler"), "links": ("id", "type", "from", "to", "marked"),
    "judgements": ("id", "about", "belief", "based_on", "reasoning"),
    "questions": ("id", "text", "answer_type", "frame"), "answers": ("id", "question", "annotator", "frame", "status"),
    "answer_evidence": ("answer", "kind", "segment"), "answer_sides": ("answer", "side", "value_text"),
    "answer_alternatives": ("answer", "alt", "status", "why"), "rejected_candidates": ("answer", "value_text", "reason"),
    "adjudication": ("id", "items", "field", "outcome", "cause"),
}
REFS = {  # (sheet, column) -> sheet whose ids it names
    ("segments", "document"): "documents", ("segments", "author"): "entities", ("segments", "written"): "times",
    ("segments", "available_from"): "times", ("segments", "related"): "segments",
    ("mentions", "segment"): "segments", ("mentions", "entity"): "entities",
    ("times", "segment"): "segments", ("times", "anchor_time"): "times",
    ("statements", "segment"): "segments", ("statements", "event_time"): "times", ("statements", "holds_from"): "times",
    ("statements", "holds_until"): "times", ("statements", "holds_at"): "times", ("statements", "due"): "times",
    ("statements", "asserted_by"): "entities", ("statements", "via"): "entities",
    ("links", "from"): "statements", ("links", "to"): "statements",
    ("judgements", "event_time"): "times", ("judgements", "holds_from"): "times", ("judgements", "holds_until"): "times",
    ("judgements", "holds_at"): "times", ("judgements", "based_on"): "statements", ("judgements", "against"): "statements",
    ("answers", "question"): "questions", ("answers", "value_entity"): "entities",
    ("answer_evidence", "answer"): "answers", ("answer_evidence", "segment"): "segments",
    ("answer_evidence", "statements"): "statements", ("answer_sides", "answer"): "answers",
    ("answer_alternatives", "answer"): "answers", ("answer_alternatives", "value_entity"): "entities",
    ("rejected_candidates", "answer"): "answers",
}
FILLER = {"entity": "entities", "time": "times", "statement": "statements"}
ITEM = ("segment", "spans", "statements", "side", "note")  # fields of an evidence item, in order


def read_sheets(folder):
    folder = Path(folder)
    sheets = {}
    for name in SHEETS:
        with open(folder / f"{name}.csv", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            sheets[name] = (reader.fieldnames, [{k: (v or "").strip() for k, v in row.items()} for row in reader])
    return sheets


def check(sheets, base=None):
    """Every problem found, as text; an empty list means the sheets export cleanly."""
    errors = []
    ids = {name: [r["id"] for r in sheets[name][1] if r.get("id")] for name in RECORDS}
    every_id = {i for v in ids.values() for i in v}
    for name, values in ids.items():
        for dup in sorted({i for i in values if values.count(i) > 1}):
            errors.append(f"{name}: id {dup} is used more than once")
    for name in SHEETS:
        for n, row in enumerate(sheets[name][1], start=2):
            at = f"{name} row {n}"
            for col in REQUIRED[name]:
                if not row.get(col):
                    errors.append(f"{at}: {col} is required")
            for col, value in row.items():
                if not value:
                    continue
                allowed = ENUMS.get((name, col))
                if col == "confidence":
                    allowed = CONFIDENCE
                if col == "inference":
                    bad = [v for v in value.split(";") if v not in INFERENCES]
                    if bad:
                        errors.append(f"{at}: inference {';'.join(bad)} is not allowed")
                elif allowed and value not in allowed:
                    errors.append(f"{at}: {col} '{value}' is not allowed")
                target = REFS.get((name, col))
                if target:
                    for ref in (value.split(";") if col in LISTS else [value]):
                        if ref not in ids[target]:
                            errors.append(f"{at}: {col} {ref} is not an id in {target}")
                if col in INTS and not value.isdigit():
                    errors.append(f"{at}: {col} '{value}' is not a whole number")
                if col == "spans" and not all(_span(s) for s in value.split(";")):
                    errors.append(f"{at}: spans '{value}' must be start-end pairs separated by ';'")
            if name == "participants":
                owners = set(ids["statements"]) | set(ids["judgements"])
                if row["owner"] and row["owner"] not in owners:
                    errors.append(f"{at}: owner {row['owner']} is not a statement or judgement")
                target = FILLER.get(row["filler_kind"])
                if target and row["filler"] not in ids[target]:
                    errors.append(f"{at}: filler {row['filler']} is not an id in {target}")
            if name == "adjudication":
                for item in row["items"].split(";"):
                    if item and item not in every_id:
                        errors.append(f"{at}: item {item} is not an id in any sheet")
    errors += _check_evidence(sheets) + _check_numbering(sheets, "answer_alternatives", "alt")
    if base is not None:
        errors += _check_text(sheets, Path(base))
    return errors


def _span(s):
    a, _, b = s.partition("-")
    return a.isdigit() and b.isdigit() and int(a) <= int(b)


def _check_evidence(sheets):
    errors = []
    status = {r["id"]: r["status"] for r in sheets["answers"][1]}
    sides = defaultdict(set)
    for r in sheets["answer_sides"][1]:
        sides[r["answer"]].add(r["side"])
    for answer, st in status.items():
        if st == "disputed" and len(sides[answer]) < 2:
            errors.append(f"answers: disputed answer {answer} needs at least two sides")
    sets = defaultdict(set)
    for n, r in enumerate(sheets["answer_evidence"][1], start=2):
        at = f"answer_evidence row {n}"
        if r["kind"] == "essential":
            if not r["set"]:
                errors.append(f"{at}: an essential item needs a set number")
            elif r["set"].isdigit():
                sets[r["answer"]].add(int(r["set"]))
        elif r["set"]:
            errors.append(f"{at}: only essential items have a set number")
        if r["side"] and r["side"] not in sides[r["answer"]]:
            errors.append(f"{at}: side {r['side']} is not a side of answer {r['answer']}")
    for answer, numbers in sets.items():
        if sorted(numbers) != list(range(1, len(numbers) + 1)):
            errors.append(f"answer_evidence: sets of {answer} must be numbered 1, 2, ... without gaps")
    return errors


def _check_numbering(sheets, name, col):
    numbers = defaultdict(list)
    for r in sheets[name][1]:
        if r[col].isdigit():
            numbers[r["answer"]].append(int(r[col]))
    return [f"{name}: {col} of {a} must be numbered 1, 2, ... in order" for a, ns in numbers.items()
            if ns != list(range(1, len(ns) + 1))]


def _check_text(sheets, base):
    """Mention and time texts must equal the document text at their offsets."""
    errors = []
    docs = {r["id"]: base / r["file"] for r in sheets["documents"][1]}
    seg_doc = {r["id"]: r["document"] for r in sheets["segments"][1]}
    texts = {d: p.read_text(encoding="utf-8") for d, p in docs.items() if p.is_file()}
    for name in ("mentions", "times"):
        for n, r in enumerate(sheets[name][1], start=2):
            text = texts.get(seg_doc.get(r["segment"]))
            if text is None or not r["start"]:
                continue
            if text[int(r["start"]):int(r["end"])] != r["text"]:
                errors.append(f"{name} row {n}: text does not match the document at {r['start']}-{r['end']}")
    return errors


def _value(row, *cols):
    return {k: (int(v) if k in INTS else v.split(";") if k in LISTS else v) for k in cols if (v := row.get(k))}


def _record(name, row):
    rec = {"record": RECORDS[name]}
    grouped = set()
    if name == "times":
        rec["value"] = {k: v for k, v in (("from", row["value_from"]), ("to", row["value_to"])) if v}
        grouped = {"value_from", "value_to"}
    if name == "questions":
        rec["about_time"] = {k: row[c] for k, c in (("text", "about_time"), ("from", "about_from"), ("to", "about_to"),
                                                    ("mode", "mode")) if row[c]}
        grouped = {"about_time", "about_from", "about_to", "mode"}
    if name == "answers":
        rec["value"] = _grouped_value(row)
        grouped = {"value_text", "value_entity", "value_forms"}
    for col, v in row.items():
        if col in grouped or not v:
            continue
        if col == "spans":
            rec[col] = [[int(x) for x in s.split("-")] for s in v.split(";")]
        else:
            rec[col] = int(v) if col in INTS else v.split(";") if col in LISTS else v
    return rec


def _grouped_value(row):
    return {k: (row[c].split(";") if k == "forms" else row[c])
            for k, c in (("text", "value_text"), ("entity", "value_entity"), ("forms", "value_forms")) if row.get(c)}


def _item(row):
    item = _value(row, "segment", "statements", "side", "note")
    if row["spans"]:
        item["spans"] = [[int(x) for x in s.split("-")] for s in row["spans"].split(";")]
    return {k: item[k] for k in ITEM if k in item}


def export(sheets, annotator):
    """{file name: [records]} for valid sheets; call check() first."""
    recs = {name: [_record(name, r) for r in sheets[name][1]] for name in RECORDS}
    by_id = {r["id"]: r for name in recs for r in recs[name] if "id" in r}
    for r in sheets["participants"][1]:
        p = {"role": r["role"], r["filler_kind"]: r["filler"]}
        if r["note"]:
            p["note"] = r["note"]
        by_id[r["owner"]].setdefault("participants", []).append(p)
    evidence = defaultdict(lambda: defaultdict(list))
    for r in sheets["answer_evidence"][1]:
        a = by_id[r["answer"]]
        if r["kind"] == "essential":
            evidence[r["answer"]][int(r["set"])].append(_item(r))
        else:
            a.setdefault("context" if r["kind"] == "context" else "counter_evidence", []).append(_item(r))
    for answer, sets in evidence.items():
        by_id[answer]["evidence"] = [sets[n] for n in sorted(sets)]
    for r in sheets["answer_sides"][1]:
        by_id[r["answer"]].setdefault("sides", []).append({"side": r["side"], "value": _grouped_value(r)})
    for r in sheets["answer_alternatives"][1]:
        alt = {"value": _grouped_value(r), **_value(r, "status", "inference", "why")}
        by_id[r["answer"]].setdefault("alternatives", []).append({k: v for k, v in alt.items() if v})
    for r in sheets["rejected_candidates"][1]:
        rej = {"value": _grouped_value(r), **_value(r, "reason", "note")}
        by_id[r["answer"]].setdefault("rejected_candidates", []).append(rej)
    seg_doc = {r["id"]: r["document"] for r in recs["segments"]}
    stmt_doc = {r["id"]: seg_doc[r["segment"]] for r in recs["statements"]}
    files = defaultdict(list)
    for name in RECORDS:
        for r in recs[name]:
            files[_file(name, r, seg_doc, stmt_doc, annotator)].append(r)
    return dict(files)


def _file(name, r, seg_doc, stmt_doc, annotator):
    doc = {"documents": lambda: r["id"], "segments": lambda: r["document"],
           "mentions": lambda: seg_doc[r["segment"]], "times": lambda: seg_doc[r["segment"]],
           "statements": lambda: seg_doc[r["segment"]],
           "links": lambda: stmt_doc[r["from"]] if stmt_doc[r["from"]] == stmt_doc[r["to"]] else None}.get(name)
    if name == "questions":
        return "questions.jsonl"
    if name == "answers":
        return f"answers.{r['annotator']}.jsonl"
    if name == "adjudication":
        return "adjudication.jsonl"
    d = doc() if doc else None
    return f"{d}.{annotator}.jsonl" if d else f"shared.{annotator}.jsonl"


def write(files, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for name, recs in files.items():
        with open(out / name, "w", encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")


def to_rows(records):
    """The inverse of export(): {sheet: [row dicts]}, used to check that nothing is lost."""
    rows = defaultdict(list)
    sheet_of = {v: k for k, v in RECORDS.items()}
    for rec in records:
        name = sheet_of[rec["record"]]
        row = {}
        for k, v in rec.items():
            if k in ("record", "participants", "evidence", "context", "counter_evidence", "sides", "alternatives",
                     "rejected_candidates"):
                continue
            if name == "times" and k == "value":
                row.update(value_from=v.get("from", ""), value_to=v.get("to", ""))
            elif name == "questions" and k == "about_time":
                row.update(about_time=v.get("text", ""), about_from=v.get("from", ""), about_to=v.get("to", ""),
                           mode=v.get("mode", ""))
            elif name == "answers" and k == "value":
                row.update(_ungroup(v))
            elif k == "spans":
                row[k] = ";".join(f"{a}-{b}" for a, b in v)
            else:
                row[k] = ";".join(v) if isinstance(v, list) else str(v)
        rows[name].append(row)
        for p in rec.get("participants", []):
            kind = next(k for k in ("entity", "time", "value", "statement") if k in p)
            rows["participants"].append({"owner": rec["id"], "role": p["role"], "filler_kind": kind,
                                         "filler": p[kind], "note": p.get("note", "")})
        for n, items in enumerate(rec.get("evidence", []), start=1):
            rows["answer_evidence"] += [_unitem(rec["id"], "essential", str(n), i) for i in items]
        rows["answer_evidence"] += [_unitem(rec["id"], "context", "", i) for i in rec.get("context", [])]
        rows["answer_evidence"] += [_unitem(rec["id"], "counter", "", i) for i in rec.get("counter_evidence", [])]
        for s in rec.get("sides", []):
            rows["answer_sides"].append({"answer": rec["id"], "side": s["side"], **_ungroup(s["value"])})
        for n, a in enumerate(rec.get("alternatives", []), start=1):
            rows["answer_alternatives"].append({"answer": rec["id"], "alt": str(n), **_ungroup(a.get("value", {})),
                                                "status": a.get("status", ""), "inference": ";".join(a.get("inference", [])),
                                                "why": a.get("why", "")})
        for c in rec.get("rejected_candidates", []):
            rows["rejected_candidates"].append({"answer": rec["id"], **_ungroup(c["value"]), "reason": c["reason"],
                                                "note": c.get("note", "")})
    return rows


def _ungroup(v):
    return {"value_text": v.get("text", ""), "value_entity": v.get("entity", ""), "value_forms": ";".join(v.get("forms", []))}


def _unitem(answer, kind, n, i):
    return {"answer": answer, "kind": kind, "set": n, "side": i.get("side", ""), "segment": i["segment"],
            "spans": ";".join(f"{a}-{b}" for a, b in i.get("spans", [])), "statements": ";".join(i.get("statements", [])),
            "note": i.get("note", "")}


def lost(sheets, files):
    """Differences between the sheets and a round trip through JSON Lines; an empty list means nothing was lost."""
    back = to_rows([r for recs in files.values() for r in recs])
    diffs = []
    for name in SHEETS:
        header, original = sheets[name]
        key = _child_key(name)
        def norm(rows):
            out = defaultdict(list)
            for r in rows:
                out[key(r)].append(tuple(r.get(c, "") or "" for c in header))
            return dict(out)
        if norm(original) != norm(back.get(name, [])):
            diffs.append(f"{name}: round trip differs")
    return diffs


def _child_key(name):
    if name == "answer_evidence":
        return lambda r: (r["answer"], r["kind"], r["set"])
    if name in ("participants",):
        return lambda r: r["owner"]
    if name in CHILDREN:
        return lambda r: r["answer"]
    return lambda r: r["id"]  # records are split across files by document, so their row order is not kept


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("sheets")
    ap.add_argument("out")
    ap.add_argument("--annotator", required=True)
    args = ap.parse_args(argv)
    sheets = read_sheets(args.sheets)
    errors = check(sheets, Path(args.sheets).parent)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    files = export(sheets, args.annotator)
    problems = lost(sheets, files)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    write(files, args.out)
    print(f"exported {sum(len(v) for v in files.values())} records to {len(files)} files; round trip lossless")
    return 0


if __name__ == "__main__":
    sys.exit(main())
