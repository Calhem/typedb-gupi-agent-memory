"""Extraction evaluation against hand-annotated conversations (tests/fixtures/conversations).

Each conversation is loaded into its own disposable database (`gupi-eval-*`), extracted, read back from
TypeDB and compared with the gold annotations. Mentions, claims and time bounds are scored separately, and
every miss or spurious claim is classified (the error taxonomy).

    uv run python -I -m gupi.evaluation --set heldout --extractor rules
"""

import argparse
import json
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from typedb.driver import TransactionType

from gupi import typeql
from gupi.extraction.contract import normalise
from gupi.extraction.pipeline import extract
from gupi.memory import Memory
from gupi.records import Batch, Context, Observation, Source
from gupi.typedb.connection import connect, transaction

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "conversations"


def load(set_name, root=FIXTURES):
    return [json.loads(p.read_text()) for p in sorted((root / set_name).glob("*.json"))]


def _utc(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)


def _window(pair):
    return None if pair is None else (_utc(pair[0] + "T00:00:00Z"), _utc(pair[1] + "T00:00:00Z"))


def run_conversation(conv, extractor, driver):
    """Extract one conversation in a fresh database; returns predicted mentions and claims in gold form."""
    db = f"gupi-eval-{uuid.uuid4().hex[:8]}"
    memory = Memory.open(db, packs=("core", "people"), driver=driver, create=True)
    try:
        source = Source(f"src:{conv['source']}", "conversation")
        context = Context(f"conv:{conv['id']}", "conversation")
        observations = [Observation(source.id, m["key"], m["text"], _utc(m["at"]), context.id) for m in conv["messages"]]
        memory.ingest(Batch((source,), tuple(observations), contexts=(context,)))
        result = extract(memory, extractor, observations)
        key_of = {o.id: o.record_key for o in observations}
        with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
            labels = {d["id"]: d["label"] for d in typeql.documents(
                tx, 'match $x isa referent; fetch { "id": $x.gupi-id, "label": $x.label };')}
            mentions = [(key_of[d["obs"]], normalise(d["text"]), d["kind"]["label"]) for d in typeql.documents(tx, """
                match $m isa mention; mentioning (container: $o, mention: $m); reference (mention: $m, referent: $x);
                      $x isa! $k;
                fetch { "obs": $o.gupi-id, "text": $m.surface-text, "kind": $k };""")]
        claims = []
        for cid in result.claims:
            v = memory.claim(cid)
            claims.append({
                "message": key_of[v.evidence[0].observation_id], "type": v.type,
                "roles": {r: normalise(labels[ids[0]]) for r, ids in v.roles.items()},
                "values": {k: normalise(x) for k, x in v.values.items()},
                "start": (v.valid.from_earliest, v.valid.from_latest) if v.valid.from_earliest else None,
                "end": (v.valid.to_earliest, v.valid.to_latest) if v.valid.to_latest else None,
                "ongoing": v.valid_to_basis == "ongoing-at-observation",
                "basis": v.basis, "id": v.id,
            })
        return {"mentions": mentions, "claims": claims, "rejected": result.rejected, "notes": result.notes}
    finally:
        driver.databases.get(db).delete()


def _key(c):
    return (c["message"], c["type"], tuple(sorted(c["roles"].items())), tuple(sorted(c["values"].items())))


def _gold_claim(g):
    return {"message": g["message"], "type": g["type"],
            "roles": {r: normalise(n) for r, n in g["roles"].items()},
            "values": {k: normalise(v) for k, v in g["values"].items()},
            "start": _window(g["start"]), "end": _window(g["end"]), "ongoing": g["ongoing"]}


def _classify_miss(g, predicted):
    same_message = [p for p in predicted if p["message"] == g["message"]]
    if not same_message:
        return "missed: nothing extracted from the message"
    if not any(p["type"] == g["type"] for p in same_message):
        return "wrong claim type"
    if not any(p["type"] == g["type"] and p["roles"] == g["roles"] for p in same_message):
        return "wrong role players"
    return "wrong attribute values"


def score(conversations, extractor, driver=None):
    driver = driver or connect()
    gold_m, pred_m, gold_c, pred_c, rejected, notes = Counter(), Counter(), [], [], [], []
    for conv in conversations:
        out = run_conversation(conv, extractor, driver)
        gold_m.update((g["message"], normalise(g["text"]), g["kind"]) for g in conv["gold"]["mentions"])
        pred_m.update(out["mentions"])
        gold_c += [_gold_claim(g) for g in conv["gold"]["claims"]]
        pred_c += out["claims"]
        rejected += out["rejected"]
        notes += out["notes"]

    m_tp = sum((gold_m & pred_m).values())
    gold_by_key = {_key(g): g for g in gold_c}
    matched = [(gold_by_key[_key(p)], p) for p in pred_c if _key(p) in gold_by_key]
    errors = Counter()
    for g in gold_c:
        if _key(g) not in {_key(p) for p in pred_c}:
            errors[_classify_miss(g, pred_c)] += 1
    errors["spurious claim"] += sum(1 for p in pred_c if _key(p) not in gold_by_key)
    time_ok = 0
    for g, p in matched:
        problems = [side for side in ("start", "end", "ongoing") if g[side] != p[side]]
        time_ok += not problems
        for side in problems:
            errors[f"time: {side} wrong"] += 1
    errors = +errors

    def pr(tp, n_pred, n_gold):
        return {"precision": round(tp / n_pred, 3) if n_pred else None,
                "recall": round(tp / n_gold, 3) if n_gold else None, "tp": tp, "predicted": n_pred, "gold": n_gold}

    return {
        "extractor": extractor.method,
        "conversations": len(conversations),
        "messages": sum(len(c["messages"]) for c in conversations),
        "mentions": pr(m_tp, sum(pred_m.values()), sum(gold_m.values())),
        "claims": pr(len(matched), len(pred_c), len(gold_c)),
        "time_correct_of_matched": {"correct": time_ok, "matched": len(matched)},
        "basis": dict(Counter(p["basis"] for p in pred_c)),
        "errors": dict(sorted(errors.items())),
        "rejected": [list(r) for r in rejected],
        "notes": notes,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--set", default="dev", choices=["dev", "heldout"])
    parser.add_argument("--extractor", default="rules", choices=["rules", "claude"])
    parser.add_argument("--max-usd", type=float, default=None, help="Claude only: cap for this run")
    args = parser.parse_args(argv)
    if args.extractor == "rules":
        from gupi.extraction.rules import RuleExtractor
        extractor = RuleExtractor()
    else:
        from gupi.extraction.claude import ClaudeExtractor
        extractor = ClaudeExtractor.from_environment(run_cap_usd=args.max_usd)
    print(json.dumps(score(load(args.set), extractor), indent=2, default=str))


if __name__ == "__main__":
    main()
