"""LoCoMo adapter: conversations -> dated session contexts, turns -> observations authored by their speaker.

Data stays in .data/ (CC BY-NC 4.0; see docs/datasets.md). Evidence turn ids (e.g. "D1:3") become the gold
turn observations. Categories follow the official evaluation code and question wording.
"""

import json
from datetime import datetime, timedelta, timezone

from gupi.benchmarks.common import ROOT, SPLIT, BenchQuestion
from gupi.extraction.contract import referent_id
from gupi.records import Batch, Context, Observation, Referent, Source

PATH = ROOT / ".data" / "locomo" / "locomo10.json"
CATEGORIES = {1: "multi-hop", 2: "temporal", 3: "open-domain", 4: "single-hop", 5: "adversarial"}
SOURCE = Source("src:locomo", "conversation", label="LoCoMo")


def load(split):
    samples = json.loads(PATH.read_text())
    wanted = set(SPLIT["locomo"][split])
    return [s for s in samples if s["sample_id"] in wanted]


def parse_date(text):
    return datetime.strptime(text.strip(), "%I:%M %p on %d %B, %Y").replace(tzinfo=timezone.utc)


def sessions(sample):
    conv = sample["conversation"]
    n = sorted(int(k.split("_")[1]) for k in conv if k.startswith("session_") and k.count("_") == 1 and isinstance(conv[k], list))
    return [(i, parse_date(conv[f"session_{i}_date_time"]), conv[f"session_{i}"]) for i in n]


def turn_text(turn):
    caption = turn.get("blip_caption")
    return turn["text"] + (f" [shared image: {caption}]" if caption else "")


def ingest(memory, clock, samples):
    """Ingest conversations in time order. Returns ({(sample id, dia id): observation id}, [observations])."""
    turn_ids, all_obs = {}, []
    for s in samples:
        sid = s["sample_id"]
        conv = s["conversation"]
        people = {name: Referent(referent_id(f"locomo:{sid}", "person", name), "person", name)
                  for name in (conv["speaker_a"], conv["speaker_b"])}
        for i, when, turns in sessions(s):
            ctx = Context(f"locomo:{sid}:s{i}", "session", f"{sid} session {i}")
            obs = []
            for j, t in enumerate(turns):
                o = Observation(SOURCE.id, f"{sid}:{t['dia_id']}", turn_text(t), when + timedelta(seconds=j), ctx.id,
                                author_id=people[t["speaker"]].id)
                turn_ids[(sid, t["dia_id"])] = o.id
                obs.append(o)
            clock.now = when + timedelta(minutes=30)
            memory.ingest(Batch((SOURCE,), tuple(obs), tuple(people.values()), contexts=(ctx,)))
            all_obs += obs
    return turn_ids, all_obs


def questions(samples, turn_ids):
    out, missing = [], 0
    for s in samples:
        sid = s["sample_id"]
        sess = sessions(s)
        contexts = [f"locomo:{sid}:s{i}" for i, _, _ in sess]
        asked = max(w for _, w, _ in sess) + timedelta(days=1)
        for n, qa in enumerate(s["qa"]):
            gold = set()
            for e in qa.get("evidence") or []:
                key = (sid, e.strip())
                if key in turn_ids:
                    gold.add(turn_ids[key])
                else:
                    missing += 1
            out.append(BenchQuestion(f"{sid}:q{n}", qa["question"], CATEGORIES[qa["category"]], contexts, asked, {"turn": gold}))
    return out, missing
