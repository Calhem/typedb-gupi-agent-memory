"""Phase 7A pipeline audit: raw dataset → adapter → observation → rules:v2 → validation → store → TypeDB.

    uv run python -I -m gupi.benchmarks.diagnosis.audit --json docs/evaluation/phase-7a/audit.json

Every check compares what one stage hands the next with what it received. Production code is called, never
changed. Output holds counts, ids, lengths and hashes only, never dataset text (the Phase 2 fixture traces,
which are synthetic and ours, are shown in full).
"""

import argparse
import hashlib
import json
import re
import sys
import uuid
from collections import Counter
from datetime import timedelta

from typedb.driver import TransactionType

from gupi import typeql
from gupi.benchmarks import locomo, longmemeval
from gupi.benchmarks.e2e import common
from gupi.extraction.contract import referent_id
from gupi.formation import evaluation as e6b, store
from gupi.formation.rules_v2 import DOMAIN_VERB, PATTERNS, SENTENCE, RulesV2
from gupi.memory import Memory
from gupi.records import Batch, Context, Observation, Referent, Source
from gupi.typedb.connection import connect, transaction

NO_PATTERN = "a domain verb, but no supported pattern"
PRONOUN = re.compile(r"^\W*(?:he|she|they|we|you|it|his|her|their|our|my|this|that)\b", re.I)
CAPITAL_AFTER_VERB = re.compile(r"\b(?:joined|left|works?|worked|working|reports?|reporting|reported|hired|promoted|"
                                r"rejoined|manages?)\b(?:\W+\w+){0,4}?\W+[A-Z][a-z]+")


def _sha(text):
    return hashlib.sha256(text.encode()).hexdigest()[:16]


# --- adapters --------------------------------------------------------------------------------------------

def locomo_adapter(samples):
    """The adapter's observations rebuilt exactly as locomo.ingest makes them, paired with the raw turns."""
    pairs = []
    for s in samples:
        sid, conv = s["sample_id"], s["conversation"]
        for i, when, turns in locomo.sessions(s):
            for j, t in enumerate(turns):
                o = Observation(locomo.SOURCE.id, f"{sid}:{t['dia_id']}", locomo.turn_text(t), when + timedelta(seconds=j),
                                f"locomo:{sid}:s{i}", author_id=referent_id(f"locomo:{sid}", "person", t["speaker"]))
                pairs.append((t, o, {"sample": sid, "session": i, "speaker": t["speaker"],
                                     "speakers": (conv["speaker_a"], conv["speaker_b"])}))
    return pairs


def check_locomo(split):
    samples = locomo.load(split)
    raw_turns = sum(len(turns) for s in samples for _, _, turns in locomo.sessions(s))
    pairs = locomo_adapter(samples)
    again = locomo_adapter(locomo.load(split))
    keys = [o.record_key for _, o, _ in pairs]
    out = {"raw_turns": raw_turns, "observations": len(pairs),
           "empty_text": sum(not o.content.strip() for _, o, _ in pairs),
           "text_equals_raw_plus_caption": sum(o.content == t["text"] + (f" [shared image: {t['blip_caption']}]" if t.get("blip_caption") else "")
                                               for t, o, _ in pairs),
           "text_shorter_than_raw": sum(len(o.content) < len(t["text"]) for t, o, _ in pairs),
           "turns_with_caption": sum(bool(t.get("blip_caption")) for t, _, _ in pairs),
           "unique_keys": len(set(keys)), "unique_observation_ids": len({o.id for _, o, _ in pairs}),
           "ids_stable_across_two_builds": [o.id for _, o, _ in pairs] == [o.id for _, o, _ in again],
           "author_matches_speaker": sum(o.author_id == referent_id(f"locomo:{m['sample']}", "person", m["speaker"])
                                         and m["speaker"] in m["speakers"] for _, o, m in pairs),
           "speakers_per_conversation": sorted({len(m["speakers"]) for _, _, m in pairs}),
           "order_within_session_increasing": _increasing(pairs, lambda m: (m["sample"], m["session"])),
           "sessions_in_date_order": _sessions_ordered(samples),
           "evidence_ids_unmatched": None}
    qs, missing = locomo.questions(samples, {(o.record_key.split(":")[0], o.record_key.split(":", 1)[1]): o.id for _, o, _ in pairs})
    out["evidence_ids_unmatched"] = missing
    return out, [o for _, o, _ in pairs]


def _increasing(pairs, group):
    last, bad = {}, 0
    for _, o, m in pairs:
        g = group(m)
        if g in last and o.observed_at <= last[g]:
            bad += 1
        last[g] = o.observed_at
    return bad == 0


def _sessions_ordered(samples):
    bad = 0
    for s in samples:
        dates = [w for _, w, _ in locomo.sessions(s)]
        bad += sum(b < a for a, b in zip(dates, dates[1:]))
    return {"sessions_dated_before_their_predecessor": bad}


def check_longmemeval(split):
    items = longmemeval.load(split)
    raw_turn_refs = sum(len(turns) for q in items for turns in q["haystack_sessions"])
    versions = {}
    for q in items:
        for sid, date, turns in zip(q["haystack_session_ids"], q["haystack_dates"], q["haystack_sessions"]):
            versions.setdefault(longmemeval.context_id(sid, date, turns), (sid, date, turns))
    obs, raw = [], []
    for cid, (sid, date, turns) in sorted(versions.items(), key=lambda kv: (longmemeval.parse_date(kv[1][1]), kv[0])):
        when = longmemeval.parse_date(date)
        for i, t in enumerate(turns):
            obs.append(Observation(longmemeval.SOURCE.id, f"{cid}:{i}", t["content"], when + timedelta(seconds=i), cid,
                                   author_id=longmemeval.ROLES[t["role"]].id))
            raw.append(t)
    out = {"questions": len(items), "turn_references_in_raw": raw_turn_refs,
           "distinct_session_versions": len(versions), "observations": len(obs),
           "empty_text": sum(not o.content.strip() for o in obs),
           "text_equals_raw": sum(o.content == t["content"] for o, t in zip(obs, raw)),
           "unique_observation_ids": len({o.id for o in obs}),
           "author_matches_role": sum(o.author_id == longmemeval.ROLES[t["role"]].id for o, t in zip(obs, raw)),
           "roles": dict(Counter(t["role"] for t in raw)),
           "order_within_session_increasing": all(
               b.observed_at > a.observed_at for a, b in zip(obs, obs[1:]) if a.context_id == b.context_id)}
    return out, obs


# --- TypeDB round trip ----------------------------------------------------------------------------------

def round_trip(driver, observations, label):
    """Ingest observations the way the benchmark adapters do and read them back from TypeDB."""
    db, clock = f"gupi-7a-audit-{uuid.uuid4().hex[:8]}", common.Clock()
    memory = Memory.open(db, packs=("core", "people"), driver=driver, create=True, clock=clock)
    try:
        by_ctx = {}
        for o in observations:
            by_ctx.setdefault(o.context_id, []).append(o)
        for ctx, os_ in by_ctx.items():
            clock.now = max(o.observed_at for o in os_) + timedelta(minutes=30)
            authors = {o.author_id for o in os_ if o.author_id}
            memory.ingest(Batch((Source(os_[0].source_id, "conversation"),), tuple(os_),
                                tuple(Referent(a, "person", a) for a in sorted(authors)), contexts=(Context(ctx, "session"),)))
        with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
            docs = typeql.documents(tx, 'match $o isa observation; fetch { "id": $o.gupi-id, "content": $o.content, '
                                        '"at": $o.observed-at, "author": [ match authorship (author: $a, authored: $o); '
                                        'fetch { "id": $a.gupi-id }; ], "ctx": [ match containment (context: $c, member: $o); '
                                        'fetch { "id": $c.gupi-id }; ] };')
        got = {d["id"]: d for d in docs}
        sent = {o.id: o for o in observations}
        return {"set": label, "sent": len(sent), "read_back": len(got),
                "content_identical": sum(got[i]["content"] == o.content for i, o in sent.items() if i in got),
                "observed_at_identical": sum(typeql.parse_datetime(got[i]["at"]) == o.observed_at for i, o in sent.items() if i in got),
                "author_preserved": sum([a["id"] for a in got[i]["author"]] == ([o.author_id] if o.author_id else [])
                                        for i, o in sent.items() if i in got),
                "context_preserved": sum([c["id"] for c in got[i]["ctx"]] == [o.context_id] for i, o in sent.items() if i in got),
                "longest_content_chars": max(len(o.content) for o in observations)}
    finally:
        driver.databases.get(db).delete()


# --- extractor -------------------------------------------------------------------------------------------

def why_no_pattern(clause):
    """A diagnostic reading of one rejected clause (evaluation heuristic, not the extractor's own reason)."""
    if any(re.compile(p).search(clause) for _, p, _, _, _ in PATTERNS):
        return "a supported phrase inside a longer clause (the patterns must match the whole clause)"
    if PRONOUN.match(clause):
        return "the subject is a pronoun or possessive"
    if not CAPITAL_AFTER_VERB.search(clause):
        return "no capitalised name after the domain verb (e.g. 'a hospital', 'my team')"
    return "other phrasing"


def run_extractor(observations):
    ex, calls, errors = RulesV2(), 0, []
    out = Counter()
    reasons, verbs, kinds = Counter(), Counter(), Counter()
    for o in observations:
        calls += 1
        try:
            cset, report = ex.extract(o)
        except Exception as e:  # the audit records exceptions; the 6D runner would have crashed on one
            errors.append((o.record_key, type(e).__name__))
            continue
        sentences = [s for s in SENTENCE.findall(o.content) if s.strip()]
        out["sentences"] += len(sentences)
        out["sentences_with_domain_verb"] += sum(bool(DOMAIN_VERB.search(s)) for s in sentences)
        out["turns_with_domain_verb"] += bool(DOMAIN_VERB.search(o.content))
        out["turns_with_newlines"] += "\n" in o.content
        out["candidates"] += len(cset.candidates)
        out["turns_with_candidates"] += bool(cset.candidates)
        for clause, reason in report.rejected:
            if reason.startswith(NO_PATTERN):
                out["clauses_domain_verb_no_pattern"] += 1
                reasons[why_no_pattern(clause)] += 1
                verbs.update(v.lower() for v in DOMAIN_VERB.findall(clause))
            else:
                out["candidates_rejected_by_validation"] += 1
                kinds[reason.split(":")[0][:60]] += 1
        out["notes"] += len(report.notes)
        for c in cset.candidates:
            kinds[f"kept {c.claim_type}"] += 1
    return {"extractor_calls": calls, "observations": len(observations), "exceptions": len(errors),
            "exception_examples": errors[:5], **dict(out),
            "why_no_pattern (diagnostic heuristic)": dict(reasons.most_common()),
            "domain_verbs_in_rejected_clauses": dict(verbs.most_common()), "validation_and_kept": dict(kinds)}


# --- representative traces -------------------------------------------------------------------------------

def stage_trace(driver, obs, label, show_text):
    """One observation through every stage, in its own database."""
    cset, report = RulesV2().extract(obs)
    db, clock = f"gupi-7a-trace-{uuid.uuid4().hex[:8]}", common.Clock(obs.observed_at)
    memory = Memory.open(db, packs=("core", "people"), driver=driver, create=True, clock=clock)
    try:
        memory.ingest(Batch((Source(obs.source_id, "conversation"),), (obs,),
                            (Referent(obs.author_id, "person", "author"),) if obs.author_id else (),
                            contexts=(Context(obs.context_id, "session"),) if obs.context_id else ()))
        clock.now = obs.observed_at + timedelta(minutes=1)
        sub = store.submit(memory, obs, cset) if cset.candidates else None
        states = [(cid, store.get(memory, cid).status) for cid in (sub.stored if sub else [])]
        c = common.counts(memory)
    finally:
        driver.databases.get(db).delete()
    return {"set": label, "key": obs.record_key, "chars": len(obs.content), "text_sha256_16": _sha(obs.content),
            **({"text": obs.content} if show_text else {}),
            "author_present": bool(obs.author_id), "context_present": bool(obs.context_id),
            "sentences": len([s for s in SENTENCE.findall(obs.content) if s.strip()]),
            "domain_verbs": sorted({v.lower() for v in DOMAIN_VERB.findall(obs.content)}),
            "extractor": {"candidates": len(cset.candidates),
                          "rejected": [r if show_text else why_no_pattern(r[0]) if r[1].startswith(NO_PATTERN) else r[1]
                                       for r in report.rejected]},
            "validation_invalid_in_store": len(sub.invalid) if sub else 0, "store_states": states,
            "typedb": {k: c[k] for k in ("observation", "memory-candidate", "formation-decision", "claim")}}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--json")
    args = p.parse_args(argv)
    driver = connect()
    result = {"meta": {**common.meta("audit", "Phase 7A pipeline audit"), "phase": "7A"}, "adapters": {}, "typedb_round_trip": [],
              "extractor": {}, "traces": []}
    lo = {}
    for split in ("dev", "heldout"):
        result["adapters"][f"locomo/{split}"], lo[split] = check_locomo(split)
        result["extractor"][f"locomo/{split}"] = run_extractor(lo[split])
    lm = {}
    for split in ("dev", "heldout"):
        result["adapters"][f"longmemeval/{split}"], lm[split] = check_longmemeval(split)
        result["extractor"][f"longmemeval/{split}"] = run_extractor(lm[split])
    result["typedb_round_trip"].append(round_trip(driver, lo["dev"], "locomo/dev (all 788 turns)"))
    longest = sorted(lm["dev"], key=lambda o: -len(o.content))[:200]
    result["typedb_round_trip"].append(round_trip(driver, longest, "longmemeval/dev (200 longest turns)"))
    phase2 = [obs for _, obs, _ in e6b.conversations("heldout")]
    phase2 = [Observation(o.source_id, o.record_key, o.content, o.observed_at, "ctx:phase2", None) for o in phase2]
    result["extractor"]["phase2/heldout (reference)"] = run_extractor(phase2)
    for o in phase2[:4]:
        result["traces"].append(stage_trace(driver, o, "phase2/heldout (synthetic, shown in full)", True))
    for split_obs, label in ((lo["dev"], "locomo/dev"), (lm["dev"], "longmemeval/dev")):
        with_verb = [o for o in split_obs if DOMAIN_VERB.search(o.content)]
        for o in sorted(with_verb, key=lambda o: _sha(o.record_key))[:3] + sorted(split_obs, key=lambda o: _sha(o.record_key))[:2]:
            result["traces"].append(stage_trace(driver, o, label + " (text withheld)", False))
    text = json.dumps(result, indent=1, default=str) + "\n"
    if args.json:
        open(args.json, "w").write(text)
    print(json.dumps({k: v for k, v in result.items() if k not in ("traces",)}, indent=1, default=str)[:6000])


if __name__ == "__main__":
    sys.exit(main())
