"""Phase 8C: real conversations through automatic extraction (docs/evaluation/phase-8c).

    uv run python -I -m gupi.benchmarks.phase8c plan
    uv run python -I -m gupi.benchmarks.phase8c extract --gate smoke --recording PATH --replay
    uv run python -I -m gupi.benchmarks.phase8c extract --gate smoke --recording PATH --live --approved-cap-usd X

Replay is the default mode of everything here. `--live` needs the owner's approved cap, which must not exceed the frozen
gate cap, and the frozen evaluation conversations also need `--approved-frozen-run`. Recordings quote the dataset, so
they must be inside `.data/`. Only counts leave this module. These are not benchmark or leaderboard results.
"""

import argparse
import hashlib
import json
import uuid
from datetime import timedelta
from pathlib import Path

from gupi.benchmarks import common, locomo
from gupi.benchmarks.__main__ import Clock
from gupi.budget import Ledger
from gupi.extraction.contract import referent_id
from gupi.formation import chat_extractor as chat
from gupi.formation.chat_extractor import ChatExtractor, Limits, LiveTransport, Recording, RunStopped
from gupi.formation.form import live_schema
from gupi.memory import Memory
from gupi.typedb.connection import connect

CONFIG_PATH = common.ROOT / "benchmarks" / "phase8c.json"
CONFIG = json.loads(CONFIG_PATH.read_text())
DATA = common.ROOT / ".data"


def samples(names):
    data = {s["sample_id"]: s for s in json.loads(locomo.PATH.read_text())}
    return [data[n] for n in names]


def authors(sample):
    conv = sample["conversation"]
    return {referent_id(f"locomo:{sample['sample_id']}", "person", n): n for n in (conv["speaker_a"], conv["speaker_b"])}


def requests(sample, turns=None):
    """(observation, author label, earlier turns) for each turn in order. Reads the file; touches no database."""
    label, out = authors(sample), []
    for i, when, session in locomo.sessions(sample):
        before = []
        for j, t in enumerate(session):
            aid = referent_id(f"locomo:{sample['sample_id']}", "person", t["speaker"])
            o = locomo.Observation(locomo.SOURCE.id, f"{sample['sample_id']}:{t['dia_id']}", locomo.turn_text(t),
                                   when + timedelta(seconds=j), f"locomo:{sample['sample_id']}:s{i}", aid)
            out.append((o, label[aid], tuple(before[-chat.CONTEXT_TURNS:])))
            before.append((label[aid], o.content))
    return out[:turns]


def estimate(names, turns=None):
    """Tokens and dollars from the actual requests. Estimated tokens are characters / 4; prompt caching is ignored."""
    e = CONFIG["estimate"]
    calls = [r for s in samples(names) for r in requests(s, turns)]
    prompt = sum(len(json.dumps([chat.build_request(*r[:2], r[2])["messages"], chat.SCHEMA])) // e["chars_per_token"] for r in calls)
    worst_in = sum(len(json.dumps(chat.build_request(*r[:2], r[2]), ensure_ascii=False).encode()) + 1000 for r in calls)
    price_in, price_out = 0.15 / 1e6, 0.60 / 1e6

    def dollars(completion):
        return round(prompt * price_in + len(calls) * completion * price_out, 2)
    return {"calls": len(calls), "prompt_tokens": prompt, "mean_prompt_tokens": prompt // max(1, len(calls)),
            "usd_typical": dollars(e["completion_tokens_typical"]), "usd_high": dollars(e["completion_tokens_high"]),
            "usd_reserved_bound": round(worst_in * price_in + len(calls) * chat.MAX_OUTPUT_TOKENS * price_out, 2)}


def plan():
    out = {name: estimate(g["conversations"], g["turns"]) | {"cap_usd": g["cap_usd"]} for name, g in CONFIG["gates"].items()}
    typical = out["frozen"]
    # Rough only: AML states "about 300M tokens" of textual data; LoCoMo averages about 38 tokens a turn here.
    turns = 300e6 / 38
    per_call_in = typical["mean_prompt_tokens"]
    out["aml_textual_scale_rough"] = {
        "turns_if_like_locomo": round(turns), "per_message_usd": round(turns * (per_call_in * .15 + 250 * .6) / 1e6),
        "per_20_messages_usd": round(turns / 20 * ((per_call_in + 19 * 40) * .15 + 20 * 250 * .6) / 1e6)}
    return out


def guard(args, gate):
    """Every reason a live run must not start, checked before a key or a ledger is touched."""
    problems = []
    if DATA.resolve() not in Path(args.recording).resolve().parents:
        problems.append("recordings quote the dataset and must be inside .data/")
    if args.live:
        if args.approved_cap_usd is None:
            problems.append("a live run needs --approved-cap-usd")
        elif args.approved_cap_usd > gate["cap_usd"]:
            problems.append(f"the cap may not exceed this gate's frozen ${gate['cap_usd']}")
        if args.gate == "frozen" and not args.approved_frozen_run:
            problems.append("the frozen conversations need --approved-frozen-run")
    return problems


def limits(calls):
    s = CONFIG["stop"]
    return Limits(calls, s["max_failure_rate"], s["check_after"], s["max_consecutive_errors"])


def build(memory, clock, sample_list, extractor, turns=None):
    """Ingest conversations, then extract each turn in order through the protected path. Approves nothing."""
    observations = []
    locomo.ingest(memory, clock, sample_list)
    schema = live_schema(memory)
    stopped = None
    try:
        for s in sample_list:
            prior = {}
            for o, author, before in requests(s, turns):
                cset, _ = extractor.extract(o, author, before, prior.get(o.context_id, ()), schema)
                prior[o.context_id] = prior.get(o.context_id, ()) + (cset,)
                clock.now += timedelta(seconds=1)
                extractor.submit(memory, o, cset)
                observations.append(o)
    except RunStopped as e:
        stopped = str(e)
    return observations, stopped


def graph_report(memory, observations, gold=frozenset()):
    """Is the automatically formed graph connected? Referents joined by a claim count as one component."""
    session = {o.id: o.context_id for o in observations}
    claims = [c for c in memory.all_claims() if c.type != "identity"]
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    players = {c.id: sorted({r for rs in c.roles.values() for r in ((rs,) if isinstance(rs, str) else rs)}) for c in claims}
    for rs in players.values():
        for r in rs[1:]:
            parent[find(r)] = find(rs[0])
    by_component, by_referent = {}, {}
    for c in claims:
        where = {session.get(e.observation_id) for e in c.evidence}
        for r in players[c.id]:
            by_referent.setdefault(r, set()).update(where)
        if players[c.id]:
            by_component.setdefault(find(players[c.id][0]), []).append(c)
    biggest = max(map(len, by_component.values()), default=0)
    linking = [c for c in claims if len(players[c.id]) >= 2]
    across = [c for c in claims if any(len(by_referent[r]) > 1 for r in players[c.id])]
    evidenced = {e.observation_id for c in claims for e in c.evidence}
    return {"claims": len(claims), "referents": len(parent), "linking_claims": len(linking),
            "linking_share": round(len(linking) / len(claims), 4) if claims else 0, "components": len(by_component),
            "largest_component_share": round(biggest / len(claims), 4) if claims else 0,
            "claims_reaching_another_session": len(across),
            "turns_with_a_claim": len(evidenced), "turn_coverage": round(len(evidenced) / max(1, len(observations)), 4),
            "gold_turns": len(gold), "gold_turns_with_a_claim": len(evidenced & set(gold))}


def readiness(tally, graph):
    """The frozen go or no-go for the next gate. Counts only; a person reads the sample as well."""
    s = CONFIG["stop"]
    parsed = sum(tally.outcomes.get(k, 0) for k in ("grounding-failure", "ambiguous-span", "invalid-model-output", "validation"))
    attempts = parsed + tally.candidates
    unusable = parsed / attempts if attempts else 1.0
    problems = []
    if unusable > s["max_unusable_share"]:
        problems.append(f"{unusable:.0%} of assertions were unusable (limit {s['max_unusable_share']:.0%})")
    if not tally.decisions.get("formed"):
        problems.append("no claim was formed")
    if graph["linking_share"] < s["min_connected_claim_share"]:
        problems.append(f"only {graph['linking_share']:.0%} of claims link two referents")
    return {"unusable_share": round(unusable, 4), "go": not problems, "problems": problems}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("command", choices=("plan", "extract"))
    p.add_argument("--gate", choices=sorted(CONFIG["gates"]), default="smoke")
    p.add_argument("--recording")
    p.add_argument("--live", action="store_true", help="make paid calls (needs the owner's approval)")
    p.add_argument("--approved-cap-usd", type=float)
    p.add_argument("--approved-frozen-run", action="store_true")
    p.add_argument("--json")
    args = p.parse_args(argv)
    if args.command == "plan":
        print(json.dumps(plan(), indent=1))
        return 0
    gate = CONFIG["gates"][args.gate]
    if problems := guard(args, gate):
        raise SystemExit("not started: " + "; ".join(problems))
    driver, db, clock = connect(), f"gupi-bench-phase8c-{uuid.uuid4().hex[:8]}", Clock()
    recording = Recording(args.recording)
    if args.live:
        calls = estimate(gate["conversations"], gate["turns"])["calls"]
        ledger = Ledger(driver, run_cap_usd=args.approved_cap_usd)
        extractor = ChatExtractor(recording, LiveTransport(), ledger, limits(calls))
    else:
        extractor = ChatExtractor(recording)
    memory = Memory.open(db, packs=("core", "people"), driver=driver, create=True, clock=clock)
    try:
        chosen = samples(gate["conversations"])
        observations, stopped = build(memory, clock, chosen, extractor, gate["turns"])
        graph = graph_report(memory, observations)
        result = {"gate": args.gate, "prompt": chat.PROMPT_HASH, "model": chat.MODEL, "stopped": stopped,
                  "config_sha256": hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest(),
                  "tally": extractor.tally.as_dict(), "graph": graph, "readiness": readiness(extractor.tally, graph),
                  "note": "Extraction counts on benchmark data; not a benchmark or leaderboard result."}
        print(json.dumps(result, indent=1))
        if args.json:
            Path(args.json).write_text(json.dumps(result, indent=1) + "\n")
    finally:
        driver.databases.get(db).delete()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
