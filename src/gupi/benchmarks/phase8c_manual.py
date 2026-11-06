"""Phase 8C: extraction by hand, inside a Claude subscription, with no API (docs/evaluation/phase-8c/manual-workflow.md).

    uv run python -I -m gupi.benchmarks.phase8c_manual export --conversations conv-30 --out DIR
    uv run python -I -m gupi.benchmarks.phase8c_manual check  --conversations conv-30 --responses FILE

`export` writes the rules and the turns, and never the questions, so the extractor stays blind to what will be asked.
Someone works through them in an interactive session and saves one JSON line per turn. `check` runs those lines through
the unchanged parser and reports what stopped. Evaluation replays them with `phase8c_eval run --responses FILE`.

Everything this module reads or writes quotes the dataset, so it must stay outside the public repository. These replies
come from a Claude model chosen by the session, not `gpt-4o-mini`, and are never presented as `gpt-4o-mini` results.
"""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from gupi.benchmarks import common, phase8c
from gupi.formation import chat_extractor as chat
from gupi.formation import store
from gupi.formation.chat_extractor import ChatExtractor, NOT_RECORDED
from gupi.formation.model_candidate import RESPONSE_FORMAT, ModelCandidateV1

FORMAT = "gupi.manual-extraction/1"
KEYS = {"e", "occ", "r", "p", "pred", "obj", "title", "t", "n", "m", "c", "b", "attr", "alleg", "corr"}
INSTRUCTIONS = """The rules below are the extraction rules, word for word. The one difference is the output.

Output: one line of JSON per turn, in order, and nothing else: {"turn": "<turn id>", "a": [ ... ]}. An empty list means \
nothing to record. Each assertion uses these short keys, and anything left out takes the stated default:
e evidence (required); occ evidence_occurrence; r relation (default statement); p participants as [role, text, kind], \
with a fourth item true if it is a pronoun or vague; pred predicate; obj object_text; title; t times as [text, kind]; \
n true if negative; m modality (default actual); c commitment (default certain); b "inferred" if inferred (default \
explicit); attr [mode, claimant, claimant_kind] (default direct, no claimant); alleg true; corr [kind, cue].

Work through the turns in order. Write each line once and do not go back. Never open anything except these files."""


def expand(assertions):
    """Short keys to the exact response format the parser takes. Only the stated defaults are added."""
    out = []
    for x in assertions:
        if unknown := set(x) - KEYS:
            raise ValueError(f"unknown keys {sorted(unknown)}")
        mode, claimant, kind = x.get("attr", ("direct", None, None))
        a = {"evidence": x["e"], "relation": x.get("r", "statement"), "times": [{"text": t, "kind": k} for t, k in x.get("t", ())],
             "participants": [{"role": q[0], "text": q[1], "kind": q[2], "is_pronoun_or_vague": bool(q[3:] and q[3])} for q in x["p"]],
             "polarity": "negative" if x.get("n") else "positive", "modality": x.get("m", "actual"), "commitment": x.get("c", "certain"),
             "basis": x.get("b", "explicit"), "attribution": {"mode": mode, "claimant": claimant, "claimant_kind": kind, "via": []}}
        for short, full in (("pred", "predicate"), ("obj", "object_text"), ("title", "title"), ("occ", "evidence_occurrence")):
            if short in x:
                a[full] = x[short]
        if x.get("alleg"):
            a["allegation"] = True
        if "corr" in x:
            a["correction"] = {"kind": x["corr"][0], "cue": x["corr"][1]}
        out.append(a)
    return {"format": RESPONSE_FORMAT, "outcome": "assertions" if out else "no-relevant-assertion", "assertions": out, "problems": []}


def read(path):
    """{turn id: compact assertions}. A repeated turn is an error: nothing is silently replaced."""
    out = {}
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            row = json.loads(line)
            if row["turn"] in out:
                raise ValueError(f"line {n}: turn {row['turn']} appears twice")
            out[row["turn"]] = row["a"]
    return out


def cause(x, message):
    """A plainer name for a stop: which words caused it. Counts only."""
    vague = [q[1].lower() for q in x["p"] if q[3:] and q[3]]
    if vague:
        head = vague[0].split()[0]
        return ": my or our" if head in ("my", "our") else ": we" if head == "we" else ": another pronoun or vague phrase"
    if any(q[1] == "I" for q in x["p"]) and "I" not in x["e"].replace("It", ""):
        return ": no stated subject"
    return ""


class ManualExtractor(ChatExtractor):
    """The same parser, tally and submit as the model path, with saved lines in place of a reply. Also counts what each
    stop cost: assertions lost, and how many of them would have linked two things."""

    def __init__(self, path):
        super().__init__(None)
        self.responses = read(path)
        self.parser = ModelCandidateV1(source=f"claude-subscription-manual:{hashlib.sha256(Path(path).read_bytes()).hexdigest()[:12]}")
        self.lost, self.lost_links = Counter(), Counter()

    def _reply(self, observation, author, before):
        entry = self.responses.get(observation.record_key)
        if entry is None:
            return dict(error=NOT_RECORDED)
        self.tally.replayed += 1
        return {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(expand(entry))}}]}

    def extract(self, observation, author, before=(), prior=(), schema=None):
        cset, report = super().extract(observation, author, before, prior, schema)
        given = self.responses.get(observation.record_key) or ()
        for o in report.outcomes:
            if o.get("assertion") is not None and o["assertion"] < len(given):
                x = given[o["assertion"]]
                kind = o["kind"] + cause(x, observation.content)
                self.lost[kind] += 1
                self.lost_links[kind] += len({q[1] for q in x["p"]}) >= 2
        return cset, report

    def submit(self, memory, observation, cset):
        super().submit(memory, observation, cset)
        for c in cset.candidates:
            status = store.get(memory, c.id).status
            if status != "formed":
                why = "held for review" if status == "review" else status
                if status == "withheld":
                    why += ": a dated event" if c.modality == "actual" else ": a plan or hypothetical"
                self.lost[why] += 1
                self.lost_links[why] += len({p.surface for p in c.participants}) >= 2


def lines(sample):
    return [f"[{o.record_key}] {author}, {o.observed_at:%Y-%m-%d}: {o.content}" for o, author, _ in phase8c.requests(sample)]


def inside_repository(path):
    return common.ROOT.resolve() in [Path(path).resolve(), *Path(path).resolve().parents]


def export(names, out):
    out = Path(out)
    if inside_repository(out):
        raise ValueError("a bundle quotes the dataset and must be outside the repository")
    if out.exists():
        raise FileExistsError(f"{out} exists: a bundle is written once")
    out.mkdir(parents=True)
    (out / "INSTRUCTIONS.md").write_text(f"{INSTRUCTIONS}\n\n{chat.SYSTEM}\n", encoding="utf-8")
    for s in phase8c.samples(names):
        (out / f"{s['sample_id']}.txt").write_text("\n".join(lines(s)) + "\n", encoding="utf-8")
    return {"format": FORMAT, "prompt": chat.PROMPT_HASH, "files": sorted(f.name for f in out.iterdir())}


def check(names, path):
    """Parser outcomes only: no database and no formation. A turn with no line is reported, not assumed empty."""
    e = ManualExtractor(path)
    wanted = [r for s in phase8c.samples(names) for r in phase8c.requests(s)]
    prior = {}
    for o, author, before in wanted:
        cset, _ = e.extract(o, author, before, prior.get(o.context_id, ()))
        prior[o.context_id] = prior.get(o.context_id, ()) + (cset,)
    t = e.tally
    extra = sorted(set(e.responses) - {o.record_key for o, _, _ in wanted})
    return {"turns": t.messages, "lines": len(e.responses), "missing": t.failures.get("no-recording", 0), "unknown_turns": extra,
            "assertions": sum(map(len, e.responses.values())), "candidates": t.candidates, "stopped": dict(e.lost),
            "stopped_that_would_link": dict(e.lost_links), "flags": dict(t.flags)}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("command", choices=("export", "check"))
    p.add_argument("--conversations", nargs="+", required=True)
    p.add_argument("--out")
    p.add_argument("--responses")
    args = p.parse_args(argv)
    if set(args.conversations) - set(phase8c.CONFIG["development"]):
        raise SystemExit("not started: manual extraction is for development conversations only")
    print(json.dumps(export(args.conversations, args.out) if args.command == "export" else check(args.conversations, args.responses), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
