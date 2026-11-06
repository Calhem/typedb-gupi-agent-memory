"""Exploratory, Phase 8C: are claims more useful as a signal of what matters than as a graph to walk?

    uv run python -I -m gupi.benchmarks.phase8c_salience --responses FILE --json PATH

**This hypothesis came from looking at development results, so nothing here is evidence of performance.** It reads
development conversations only and has no option for held-out data. Every claim variant has a text-only control that
gets the same treatment. Also measures, for the extraction efficiency design, how much a cheap text filter would keep.
"""

import argparse
import json
import re
import statistics
import uuid
from pathlib import Path

from gupi import paths
from gupi.benchmarks import locomo, phase8c, phase8c_eval as ev
from gupi.benchmarks.__main__ import Clock
from gupi.benchmarks.phase8c_manual import ManualExtractor
from gupi.memory import Memory
from gupi.typedb.connection import connect

K = (5, 10, 100)
SELF_REPORT = re.compile(r"\b(?:I|I'm|I've|I'd|my|My|we|We|our|Our)\b")
FACTUAL = re.compile(r"\b(?:\d{4}|yesterday|today|last|next|ago|recently|lately|since|went|got|started|joined|moved|bought|made|took|met|"
                     r"visited|finished|painted|signed|applied|passed|ran|work|working|live|love|loved)\b", re.I)
ACK = re.compile(r"^(?:thanks|thank you|wow|yeah|yes|yep|bye|sure|no prob|no worries|glad|awesome|cool|nice|great|congrats)\b", re.I)


def worth_reading(text):
    """The cheap text filter: a statement about the speaker with something factual in it, ignoring image captions."""
    text = text.split(" [shared image:")[0]
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text) if s and not s.endswith("?")]
    return any(SELF_REPORT.search(s) and FACTUAL.search(s) and not ACK.search(s) for s in sentences)


def promote(ranked, signalled, keep):
    """Top `keep` stay; then signalled turns alternate with the rest. Nothing is removed."""
    head, rest = ranked[:keep], ranked[keep:]
    return list(dict.fromkeys(head + paths.interleave([o for o in rest if o in signalled], [o for o in rest if o not in signalled]) + rest))


def add_all(ranked, signalled, keep):
    """As `promote`, but every signalled turn in scope is a candidate, whether or not the words matched."""
    return list(dict.fromkeys(ranked[:keep] + paths.interleave(sorted(signalled - set(ranked[:keep])), ranked[keep:]) + ranked))


def efficiency(requests, formed, linking, gold):
    kept = {o.id for o, _, _ in requests if worth_reading(o.content)}
    everything = {o.id for o, _, _ in requests}

    def share(group):
        return round(len(group & kept) / len(group), 3) if group else None
    return {"turns": len(everything), "kept_share": share(everything), "turns_with_a_claim_kept": share(formed),
            "linking_turns_kept": share(linking), "gold_turns_kept": share(gold)}


def scale_table(turns=300e6 / 38, fixed=1880, per_turn=40, context=80, output_empty=30, per_assertion=130, assertions_per_turn=.354,
                kept=.266, claims_kept=.694):
    """Rough extraction cost at AML's stated corpus size, in dollars, from measured rates. None of this has been run. A
    window replaces the two context turns per message, since its turns are each other's context."""
    def cost(calls, tokens_in, tokens_out):
        return round((calls * tokens_in * .15 + tokens_out * .60) / 1e6)
    per_output = output_empty + assertions_per_turn * per_assertion
    out = {}
    for window in (1, 5, 20):
        prompt = fixed + window * per_turn + (context if window == 1 else 0)
        envelope = output_empty if window == 1 else 8
        output = envelope + assertions_per_turn * per_assertion
        out[f"every turn, {window} per request"] = {"calls": round(turns / window), "usd": cost(turns / window, prompt, turns * output)}
        out[f"text filter, {window} per request"] = {"calls": round(turns * kept / window), "usd": cost(
            turns * kept / window, prompt, turns * (kept * envelope + claims_kept * assertions_per_turn * per_assertion))}
    return {"turns": round(turns), "single_output_estimate": round(per_output), "rows": out}


def run(responses):
    names = phase8c.CONFIG["development"]
    driver, db, clock = connect(), f"gupi-bench-phase8c-{uuid.uuid4().hex[:8]}", Clock()
    memory = Memory.open(db, packs=("core", "people"), driver=driver, create=True, clock=clock)
    try:
        sample_list = phase8c.samples(names)
        observations, _ = phase8c.build(memory, clock, sample_list, ManualExtractor(responses))
        turn_ids = {tuple(o.record_key.split(":", 1)): o.id for o in observations}
        questions = ev.dev_questions(sample_list, locomo.questions(sample_list, turn_ids)[0])
        texts = {o.id: o.content for o in observations}
        claims = [c for c in memory.all_claims() if c.type != "identity"]
        claimed = {e.observation_id for c in claims for e in c.evidence}
        linking = {e.observation_id for c in claims if sum(len((r,) if isinstance(r, str) else r) for r in c.roles.values()) >= 2 for e in c.evidence}
        filtered = {o for o, t in texts.items() if worth_reading(t)}
        budget = paths.Budget(k=400, pool=100, keep=3)
        rows = []
        for q in questions:
            gold = q.gold["turn"]
            if not gold:
                continue
            base = paths.conversational(memory, q.text, q.contexts, budget)
            scope = set(base.scope)
            variants = {"B-conversational": base.ids,
                        "E1-promote-claim-turns": promote(base.ids, claimed, 3), "E1c-promote-text-filter": promote(base.ids, filtered, 3),
                        "E2-add-claim-turns": add_all(base.ids, claimed & scope, 3), "E2c-add-text-filter": add_all(base.ids, filtered & scope, 3)}
            for name, ranked in variants.items():
                rows.append({"question": q.id, "stratum": q.category, "system": name, **{f"recall@{k}": len(set(ranked[:k]) & gold) / len(gold) for k in K}})
        out = {}
        for s in sorted({r["stratum"] for r in rows}):
            out[s] = {n: {f"recall@{k}": round(statistics.mean(r[f"recall@{k}"] for r in rows if r["system"] == n and r["stratum"] == s), 4) for k in K}
                      for n in dict.fromkeys(r["system"] for r in rows)}
        gold = {g for q in questions for g in q.gold["turn"]}
        return {"note": "Exploratory, development data, hypothesis formed from these results. Not evidence of performance.",
                "questions": {s: sum(r["stratum"] == s and r["system"] == "B-conversational" for r in rows) for s in out}, "recall": out,
                "base_rates": {"turns": len(texts), "claim_turns": len(claimed), "text_filter_turns": len(filtered), "gold_turns": len(gold),
                               "gold_in_claim_turns": len(gold & claimed), "gold_in_text_filter": len(gold & filtered)},
                "efficiency": efficiency([r for s in sample_list for r in phase8c.requests(s)], claimed, linking, gold),
                "scale": scale_table()}
    finally:
        driver.databases.get(db).delete()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--responses", required=True)
    p.add_argument("--json")
    args = p.parse_args(argv)
    result = run(args.responses)
    print(json.dumps(result, indent=1))
    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
