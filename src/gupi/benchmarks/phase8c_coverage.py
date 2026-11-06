"""Phase 8C: what do the parser and formation rules exclude, even from a perfect extraction?

    uv run python -I -m gupi.benchmarks.phase8c_coverage --json PATH

Part one feeds the best reply a model could give, for each construct in invented messages, through the real parser and
formation policy, and names the stage that stopped it. Part two counts how often each construct occurs in the LoCoMo
development conversations, by pattern. Counts only: no conversation text leaves this module. Nothing calls a model.
"""

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from gupi.benchmarks import phase8c
from gupi.formation import form as policy
from gupi.formation.model_candidate import RESPONSE_FORMAT, ModelCandidateV1
from gupi.records import Observation

WHEN = datetime(2023, 5, 8, 13, 0, tzinfo=timezone.utc)
AUTHOR = "p:juno"
# which part of the system each parser stop belongs to
ORIGIN = {"grounding-failure": "parsing", "ambiguous-span": "parsing", "ambiguous-reference": "identity resolution",
          "inferred-not-admissible": "extraction policy", "cue-conflict": "parsing", "validation": "parsing",
          "invalid-model-output": "extraction"}


def p(role, text, kind="person", vague=False):
    return {"role": role, "text": text, "kind": kind, "is_pronoun_or_vague": vague}


def a(evidence, participants, relation="statement", predicate=None, obj=None, times=(), **over):
    out = {"evidence": evidence, "relation": relation, "participants": participants, "times": [{"text": t, "kind": k} for t, k in times],
           "polarity": "positive", "modality": "actual", "commitment": "certain", "basis": "explicit",
           "attribution": {"mode": "direct", "claimant": None, "claimant_kind": None, "via": []}}
    if predicate:
        out["predicate"] = predicate
    if obj:
        out["object_text"] = obj
    return out | over


EMPLOYER = ("employer", "Meridian", "organization")
ME = p("subject", "I")
# (group, label, message, the best possible assertion, earlier turn or None)
CASES = (
    ("first person", "plain employment", "I work at Meridian.", a("I work at Meridian", [p("employee", "I"), p(*EMPLOYER)], "employment")),
    ("first person", "with a start", "I joined Meridian in 2021.", a("I joined Meridian in 2021", [p("employee", "I"), p(*EMPLOYER)], "employment", times=[("2021", "start")])),
    ("first person", "contraction", "I've worked at Meridian since 2021.", a("I've worked at Meridian since 2021", [p("employee", "I"), p(*EMPLOYER)], "employment", times=[("since 2021", "holds-since")])),
    ("first person", "capital I inside a word", "I work at Meridian in Italy.", a("I work at Meridian in Italy", [p("employee", "I"), p(*EMPLOYER)], "employment")),
    ("first person", "second I in the span", "I think I met Bram Oster.", a("I met Bram Oster", [ME, p("object", "Bram Oster")], predicate="met")),
    ("first person", "two I in the smallest span", "I said I met Bram Oster.", a("I said I met Bram Oster", [ME, p("object", "Bram Oster")], predicate="said I met")),
    ("first person", "no second referent", "I volunteer at a shelter.", a("I volunteer at a shelter", [ME], predicate="volunteer at", obj="a shelter")),
    ("my X", "bare relation", "My sister moved to Oslo.", a("My sister moved to Oslo", [p("subject", "My sister", vague=True), p("object", "Oslo", "unclassified")], predicate="moved to")),
    ("my X", "relation with a name, the fact", "My sister Kate moved to Oslo.", a("Kate moved to Oslo", [p("subject", "Kate"), p("object", "Oslo", "unclassified")], predicate="moved to")),
    ("my X", "relation with a name, the kinship", "My sister Kate moved to Oslo.", a("My sister Kate", [p("subject", "I"), p("object", "Kate")], predicate="sister")),
    ("my X", "my manager", "My manager Dana Voss approved it.", a("My manager Dana Voss", [p("report", "My", vague=True), p("manager", "Dana Voss")], "reporting")),
    ("my X", "I report to", "I report to Dana Voss.", a("I report to Dana Voss", [p("report", "I"), p("manager", "Dana Voss")], "reporting")),
    ("my X", "my colleague", "My colleague Bram joined Meridian.", a("Bram joined Meridian", [p("employee", "Bram"), p(*EMPLOYER)], "employment")),
    ("one-time event", "no time", "I ran the Oslo marathon.", a("I ran the Oslo marathon", [ME, p("object", "Oslo marathon", "unclassified")], predicate="ran")),
    ("one-time event", "relative week", "I ran the marathon last week.", a("I ran the marathon last week", [ME], predicate="ran", obj="the marathon", times=[("last week", "holds-at")])),
    ("one-time event", "yesterday", "I ran the marathon yesterday.", a("I ran the marathon yesterday", [ME], predicate="ran", obj="the marathon", times=[("yesterday", "holds-at")])),
    ("one-time event", "exact day", "I ran the marathon on 3 May 2023.", a("I ran the marathon on 3 May 2023", [ME], predicate="ran", obj="the marathon", times=[("on 3 May 2023", "holds-at")])),
    ("one-time event", "a year", "I went to Oslo in 2022.", a("I went to Oslo in 2022", [ME, p("object", "Oslo", "unclassified")], predicate="went to", times=[("in 2022", "holds-at")])),
    ("one-time event", "read as a start", "I moved to Oslo in 2022.", a("I moved to Oslo in 2022", [ME, p("object", "Oslo", "unclassified")], predicate="moved to", times=[("in 2022", "start")])),
    ("multi-turn", "pronoun for a named person", "She works at Meridian.", a("She works at Meridian", [p("employee", "She", vague=True), p(*EMPLOYER)], "employment")),
    ("multi-turn", "fragment answer", "At Meridian.", a("At Meridian", [p("employee", "I"), p(*EMPLOYER)], "employment")),
    ("multi-turn", "that refers back", "That was in 2021.", a("That was in 2021", [p("subject", "That", vague=True)], predicate="was", times=[("2021", "holds-at")])),
    ("implicit", "no subject", "Went to Oslo last week.", a("Went to Oslo last week", [p("subject", "I"), p("object", "Oslo", "unclassified")], predicate="Went to", times=[("last week", "holds-at")])),
    ("implicit", "no object", "I loved it!", a("I loved it", [ME, p("object", "it", "unclassified", vague=True)], predicate="loved")),
    ("implicit", "inferred, declared", "Got the job at Meridian!", a("Got the job at Meridian", [p("employee", "I"), p(*EMPLOYER)], "employment", basis="inferred")),
    ("protections", "hedge", "I think Bram works at Meridian.", a("Bram works at Meridian", [p("employee", "Bram"), p(*EMPLOYER)], "employment")),
    ("protections", "a plan", "I will join Meridian.", a("I will join Meridian", [p("employee", "I"), p(*EMPLOYER)], "employment")),
    ("protections", "negation", "I never worked at Meridian.", a("I never worked at Meridian", [p("employee", "I"), p(*EMPLOYER)], "employment")),
)


def probe(group, label, message, assertion):
    obs = Observation("src:probe", label, message, WHEN, "s1", AUTHOR)
    response = {"format": RESPONSE_FORMAT, "outcome": "assertions", "assertions": [assertion], "problems": []}
    cset, report = ModelCandidateV1().extract(obs, response=response)
    if not cset.candidates:
        kind = report.outcomes[0]["kind"]
        return {"group": group, "case": label, "result": kind, "origin": ORIGIN.get(kind, kind), "links": False}
    c = cset.candidates[0]
    d = policy.decide(c, [], {})
    result = d.outcome
    origin = "none" if result == "formed" else "formation policy"
    return {"group": group, "case": label, "result": result, "origin": origin, "links": len({x.surface for x in c.participants}) >= 2,
            "why": None if result == "formed" else d.reason[:90]}


PATTERNS = {
    "first person": re.compile(r"\bI\b"),
    "first person, a capital I elsewhere in the sentence": None,
    "my + relation word": re.compile(r"\b[Mm]y (?:\w+ )?(?:sister|brother|mom|mum|dad|mother|father|wife|husband|partner|boyfriend|girlfriend|son|daughter|kids?|children|family|friends?|colleagues?|manager|boss|coworkers?|team|cousin|aunt|uncle|grand\w+|neighbou?rs?|parents?)\b"),
    "my + anything": re.compile(r"\b[Mm]y \w+"),
    "starts with a pronoun": re.compile(r"^(?:He|She|They|It|That|This|Those|These|You|We)\b"),
    "relative time": re.compile(r"\b(?:yesterday|today|tomorrow|last (?:week|month|year|night|weekend|Friday|Saturday|Sunday|Monday|Tuesday|Wednesday|Thursday)|next (?:week|month|year)|\d+ (?:days|weeks|months|years) ago|recently|lately)\b", re.I),
    "past-tense action": re.compile(r"\b(?:went|got|started|joined|moved|bought|made|took|met|visited|finished|won|lost|began|tried|saw|found|had a)\b", re.I),
    "fragment, no subject": re.compile(r"^(?:Went|Got|Just|Started|Finished|Loved|Thanks|Thank|Glad|Sounds|Wow|Yeah|Yes|No|Sure|Nice|Great|Awesome|Cool|Love|Totally)\b"),
    "question": re.compile(r"\?\s*$"),
    "name mid-sentence": re.compile(r"(?<=[a-z,;:] )[A-Z][a-z]+\b"),
}


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def frequencies(names):
    counts, turns, total = Counter(), Counter(), 0
    all_turns = 0
    for s in phase8c.samples(names):
        for o, _, _ in phase8c.requests(s):
            all_turns += 1
            hit = set()
            for sent in sentences(o.content):
                total += 1
                for k, pattern in PATTERNS.items():
                    found = sent.count("I") > 1 and PATTERNS["first person"].search(sent) if pattern is None else pattern.search(sent)
                    if found:
                        counts[k] += 1
                        hit.add(k)
            turns.update(hit)
    return {"turns": all_turns, "sentences": total,
            "by_sentence": {k: {"count": counts[k], "share": round(counts[k] / total, 3)} for k in PATTERNS},
            "by_turn": {k: {"count": turns[k], "share": round(turns[k] / all_turns, 3)} for k in PATTERNS}}


def run(names=("conv-26", "conv-30")):
    return {"probes": [probe(*c) for c in CASES], "frequencies": frequencies(list(names)),
            "note": "Best-case replies on invented messages, and pattern counts on development data. Not an extraction result."}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json")
    args = ap.parse_args(argv)
    result = run()
    for r in result["probes"]:
        print(f"{r['group']:15} {r['case']:36} {r['result']:24} {r['origin']:20} {'links' if r['links'] else ''}")
    for k, v in result["frequencies"]["by_turn"].items():
        print(f"{k:55} {v['count']:4} turns {v['share']:.0%}")
    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
