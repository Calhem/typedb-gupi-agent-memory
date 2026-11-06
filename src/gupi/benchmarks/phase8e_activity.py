"""Phase 8E: can activities be represented without speculation? A temporary, in-memory test.

    uv run python -I -m gupi.benchmarks.phase8e_activity --ledger PRIVATE_FILE --responses PRIVATE_FILE --json PATH

**Not a schema, not a feature and not an evaluation.** It adds nothing to TypeDB. A person writes a ledger of activities, each
mention carrying its role and how sure the link is. This turns the clear mentions into engagement evidence and asks the
unchanged `answering_v2.classify`, so confirmed, presumed, unknown and ended mean exactly what they mean for employment.

The ledger, questions and per-question output quote the conversation, so they stay outside the repository. Only counts and
opaque ids leave this module. The comparison is circular by construction: the ledger defines what counts as support, so
it shows what each representation can express, never how well anything performs.
"""

import argparse
import json
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from gupi import paths, timeexpr
from gupi.answering_v2 import classify
from gupi.temporal import Answer, ValidTime

ROLES = ("start", "resume", "end", "past", "engagement", "negated", "event", "plan", "reference")
SAME = ("clear", "probable", "unclear")
STATES = {Answer.TRUE: "confirmed", Answer.PRESUMED: "presumed", Answer.UNKNOWN: "unknown", Answer.FALSE: "ended",
          Answer.CONTESTED: "contested", Answer.NOT_YET_KNOWN: "unknown"}
ENGAGEMENT_ROLES = ("start", "resume", "end", "past", "engagement", "negated")


@dataclass(frozen=True)
class Mention:
    key: str                  # the turn
    quote: str
    role: str                 # start, resume, end, past, engagement, negated, event, plan, reference
    said_at: datetime
    same: str = "clear"       # is this clearly the same activity? Anything else is recorded and never used
    time: str | None = None   # the time words, exactly as written
    replaces: str | None = None   # a correction: the key of the mention it replaces


@dataclass(frozen=True)
class Activity:
    id: str
    person: str
    kind: str
    mentions: tuple
    word: str = ""            # the word someone might naively match on
    ambiguity: str | None = None

    def used(self):
        replaced = {m.replaces for m in self.mentions if m.replaces}
        return [m for m in self.mentions if m.same == "clear" and m.key not in replaced]


def evidence_item(m):
    """A mention as a claim-shaped object the classifier reads. Time words are read by the same reader as every claim, and
    an unreadable phrase gives no bound: nothing is invented. A plain statement holds at the moment it was said, and no
    further: that is why two mentions never make a period."""
    r = timeexpr.read(m.time, m.said_at, "past") if m.time else None
    if m.role in ("start", "resume"):
        v = ValidTime(r.earliest, r.latest) if r else ValidTime(from_latest=m.said_at)
    elif m.role == "end":
        v = ValidTime(to_earliest=r.earliest, to_latest=r.latest) if r else ValidTime(to_latest=m.said_at)
    elif m.role == "past":
        v = ValidTime(to_latest=m.said_at)                # "used to": over by the time it was said; when is not stated
    else:
        v = ValidTime(to_earliest=m.said_at)
    return SimpleNamespace(id=f"{m.key}:{m.role}", valid=v, polarity="negative" if m.role == "negated" else "positive")


def status(activity, at, believed_at=None):
    """(state, the mentions that decided it) at moment `at`, on what was known by `believed_at`, by default everything. As
    everywhere in GUPI, when something was true and when it was known are separate questions."""
    mentions = [m for m in activity.used() if m.role in ENGAGEMENT_ROLES]
    known = [evidence_item(m) for m in mentions if believed_at is None or m.said_at <= believed_at]
    r = classify(known, at, True) if known else None
    if r is None:
        return "unknown", ()
    return STATES[r.answer], r.basis.claims


def resumed(activity):
    """A stated start after a stated end. Reappearing in conversation is never a resumption."""
    used = sorted(activity.used(), key=lambda m: m.said_at)
    ended = False
    for m in used:
        ended = ended or m.role in ("end", "past")
        if ended and m.role == "resume":
            return True
    return False


def unreconciled(activity):
    """Statements that it held and that it did not, with no stated start or end between them. The classifier sees these as
    separate moments, so it never says contested. Without this check a contradiction reads as a story: it stopped, then
    started again. Reported, never resolved."""
    used = sorted((m for m in activity.used() if m.role in ENGAGEMENT_ROLES), key=lambda m: m.said_at)
    flips = 0
    for a, b in zip(used, used[1:]):
        flips += {a.role, b.role} == {"engagement", "negated"}
    return flips


def relationship(activity):
    """What the evidence establishes about person and activity. Plans and events alone establish no engagement."""
    roles = {m.role for m in activity.used()}
    if unreconciled(activity):
        return "contradictory"
    if roles & {"end", "past"}:
        return "ended"
    return "established" if roles & {"start", "resume", "engagement"} else "unknown"


def trajectory(activity, moments):
    """The state over time with repeats removed: what changed, and nothing else. A statement is confirmed only at its own
    instant, so confirmed and presumed read together as engaged here."""
    out = []
    for at in moments:
        state = status(activity, at)[0]
        state = "engaged" if state in ("confirmed", "presumed") else state
        if not out or out[-1] != state:
            out.append(state)
    return out


def load(path, said_at):
    """Activities from a ledger. `said_at` gives each turn's time."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Activity(a["id"], a["person"], a["kind"], tuple(Mention(m["turn"], m["quote"], m["role"], said_at[m["turn"]], m.get("same", "clear"),
                                                                    m.get("time"), m.get("replaces")) for m in a["mentions"]),
                     a.get("word", ""), a.get("ambiguity")) for a in data["activities"]], data.get("questions", [])


def check(activities, texts, authors):
    """Every quote must be in its turn, word for word, and spoken by the person unless marked otherwise."""
    problems = []
    for a in activities:
        for m in a.mentions:
            if m.role not in ROLES or m.same not in SAME:
                problems.append(f"{a.id} {m.key}: unknown role or link")
            if m.key not in texts or m.quote not in texts[m.key]:
                problems.append(f"{a.id} {m.key}: the quote is not in that turn")
            elif authors.get(m.key) != a.person:
                problems.append(f"{a.id} {m.key}: not said by {a.person}")
    return problems


def word_matches(activity, claims, speaker):
    """The best a repeated-word link can do on today's claims: this person's claims whose object text holds this word."""
    return [c for c in claims if activity.word and activity.word in str(c.values.get("object-text", "")).lower()
            and speaker.get(c.evidence[0].observation_id) == activity.person]


def coverage(activity, claims_by_turn):
    """How much of an activity's story already exists as claims, and how scattered it is."""
    used = activity.used()
    formed = [m for m in used if any(m.quote[:12] in q or q[:12] in m.quote for q, _ in claims_by_turn.get(m.key, ()))]
    predicates = {p for m in formed for _, p in claims_by_turn.get(m.key, ())}
    boundary = [m for m in used if m.role in ("start", "end", "resume", "past")]
    return {"mentions": len(used), "with_a_formed_claim": len(formed), "distinct_predicates": len(predicates), "boundaries": len(boundary),
            "boundaries_as_claims": sum(m in formed for m in boundary)}


def evaluate(activities, questions, memory, claims, owners, speaker, contexts):
    """Exploratory, developer-written questions. For each: did raw retrieval return the supporting turns, did a word match
    on claims, and what does the activity model state directly?"""
    by_id = {a.id: a for a in activities}
    last = max(m.said_at for a in activities for m in a.mentions) + timedelta(days=1)
    rows = []
    budget = paths.Budget(k=100, pool=100)
    for q in questions:
        scope = [by_id[i] for i in q["activities"]]
        support = {f"{m.key}" for a in scope for m in a.used() if m.role in q["roles"]}
        turn_id = q["_turn_ids"]
        wanted = {turn_id[t] for t in support}
        ranked = paths.conversational(memory, q["text"], contexts, budget).ids
        hits = {c.evidence[0].observation_id for a in scope for c in word_matches(a, claims, speaker)}
        foreign = sum(1 for a in scope for c in word_matches(a, claims, speaker) if a.id not in owners.get(c.evidence[0].observation_id, ()))
        rows.append({"id": q["id"], "type": q["type"], "support": len(wanted),
                     "raw_top10": len(wanted & set(ranked[:10])), "raw_top100": len(wanted & set(ranked)), "claim_word_match": len(wanted & hits),
                     "claim_word_foreign": foreign, "model_support": len(wanted),
                     "model_state": [status(a, last)[0] for a in scope]})
    return rows


def summarise(rows):
    out = {}
    for t in sorted({r["type"] for r in rows}):
        sel = [r for r in rows if r["type"] == t]
        total = sum(r["support"] for r in sel)
        out[t] = {"questions": len(sel), "support_turns": total, "raw_top10": sum(r["raw_top10"] for r in sel), "raw_top100": sum(r["raw_top100"] for r in sel),
                  "claim_word_match": sum(r["claim_word_match"] for r in sel), "claim_word_foreign": sum(r["claim_word_foreign"] for r in sel)}
    return out


def run(ledger, responses, conversation="conv-30"):
    from gupi.benchmarks import locomo, phase8c
    from gupi.benchmarks.__main__ import Clock
    from gupi.benchmarks.phase8c_manual import ManualExtractor
    from gupi.memory import Memory
    from gupi.typedb.connection import connect
    sample = phase8c.samples([conversation])[0]
    requests = phase8c.requests(sample)
    short = {o.record_key.split(":", 1)[1]: o for o, _, _ in requests}
    speaker = {o.record_key.split(":", 1)[1]: author for o, author, _ in requests}
    activities, questions = load(ledger, {k: o.observed_at for k, o in short.items()})
    texts = {k: o.content for k, o in short.items()}
    if problems := check(activities, texts, speaker):
        raise SystemExit("ledger problems:\n" + "\n".join(problems))
    driver, db, clock = connect(), f"gupi-bench-phase8e-{uuid.uuid4().hex[:8]}", Clock()
    memory = Memory.open(db, packs=("core", "people"), driver=driver, create=True, clock=clock)
    try:
        keep = {line for line in Path(responses).read_text(encoding="utf-8").splitlines() if f'"{conversation}:' in line}
        scoped = Path(responses).with_suffix(".scoped.tmp")
        scoped.write_text("\n".join(sorted(keep)) + "\n", encoding="utf-8")
        phase8c.build(memory, clock, [sample], ManualExtractor(scoped))
        scoped.unlink()
        claims = [c for c in memory.all_claims() if c.type != "identity"]
        back = {o.id: k for k, o in short.items()}
        by_turn = {}
        for c in claims:
            for e in c.evidence:
                by_turn.setdefault(back[e.observation_id], []).append((e.quote, c.values.get("predicate-text") or c.type))
        owners = {}
        for a in activities:
            for m in a.mentions:
                owners.setdefault(short[m.key].id, set()).add(a.id)
        moments = sorted({locomo.sessions(sample)[i][1] for i in range(len(locomo.sessions(sample)))})
        turn_ids = {k: o.id for k, o in short.items()}
        for q in questions:
            q["_turn_ids"] = turn_ids
        contexts = [f"locomo:{sample['sample_id']}:s{i}" for i, _, _ in locomo.sessions(sample)]
        by_obs = {o.id: speaker[k] for k, o in short.items()}
        rows = evaluate(activities, questions, memory, claims, owners, by_obs, contexts)
        end = moments[-1] + timedelta(days=1)
        table = []
        for a in activities:
            used = a.used()
            table.append({"id": a.id, "kind": a.kind, "mentions": len(a.mentions), "clear": len(used), "not_linked": len(a.mentions) - len(used),
                          "roles": dict(Counter(m.role for m in used)), "ambiguous": bool(a.ambiguity), "after_the_last_session": status(a, end)[0],
                          "trajectory": trajectory(a, moments + [end]), "resumed": resumed(a), "relationship": relationship(a),
                          "unreconciled_flips": unreconciled(a), "existing_claims": coverage(a, by_turn),
                          "word_links": _word_report(a, claims, owners, by_obs)})
        return {"note": "Exploratory, developer-written, circular by construction. Not an evaluation.", "conversation": conversation,
                "claims": len(claims), "activities": table, "questions": summarise(rows)}, rows
    finally:
        driver.databases.get(db).delete()


def _word_report(a, claims, owners, speaker):
    hit = word_matches(a, claims, speaker)
    wrong = [c for c in hit if a.id not in owners.get(c.evidence[0].observation_id, ())]
    return {"matched": len(hit), "other_or_unassigned": len(wrong)}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--ledger", required=True)
    p.add_argument("--responses", required=True)
    p.add_argument("--json")
    p.add_argument("--rows", help="per-question rows; private")
    args = p.parse_args(argv)
    result, rows = run(args.ledger, args.responses)
    print(json.dumps(result, indent=1))
    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=1) + "\n")
    if args.rows:
        Path(args.rows).write_text(json.dumps(rows, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
