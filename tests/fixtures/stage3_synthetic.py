"""Small synthetic fixtures for the Stage 3 scorer's tests. Developer-authored, fictional, and separate from
the Stage 3 evaluation corpus (no passage, name or gold assertion is shared with it)."""

import copy
import json

from gupi.benchmarks.phase7b import annotations as ann
from gupi.benchmarks.phase7b.stage3 import text_hash
from gupi.formation.model_candidate import RESPONSE_FORMAT

FWD = "FYI.\n---- Forwarded message ----\nFrom: Hal Ostrow\nIlse Varga chairs the Corvan Freight audit panel."


def passage(pid, text, thread=None, turn=None, author="Rui Banks", kind="email", date="2025-06-10"):
    return {"passage_id": pid, "thread_id": thread, "turn": turn, "document_kind": kind, "stated_author": author,
            "document_date": date, "metadata": {"source": "synthetic test fixture"}, "text": text, "sha256": text_hash(text)}


PASSAGES = [
    passage("S-01", "Ilse Varga joined Corvan Freight as general counsel in May 2025."),
    passage("S-02", "According to Tamsin Oduya, Ilse Varga reports to Piet Marr."),
    passage("S-03", "Ilse Varga left Corvan Freight in June 2025.", "T1", 1, kind="chat"),
    passage("S-04", "Correction: Ilse Varga left Corvan Freight in July 2025, not June.", "T1", 2, kind="chat"),
    passage("S-05", "Ilse Varga joined Brightmere in March 2025.", "T2", 1, kind="chat"),
    passage("S-06", "Ilse Varga joined Brightmere in February 2025.", "T2", 2, kind="chat"),
    passage("S-07", "Scratch that: Ilse Varga joined Brightmere in April 2025.", "T2", 3, kind="chat"),
    passage("S-08", "Thanks for the update on Corvan Freight, see you Monday."),
    passage("S-09", FWD, "T3", 1, author="Rui Banks"),
    passage("S-10", FWD, "T3", 2, author="Wen Abara"),
]


def gold(aid, pid, span, ctype, participants, **kw):
    g = {k: "" for k in ann.ASSERTION_COLUMNS}
    g.update(assertion_id=aid, passage_id=pid, span_text=span, relation=ctype, gupi_claim_type=ctype,
             participants=participants, source_speaker="Rui Banks", attribution_mode="direct", independent_origin="yes",
             polarity="positive", modality="actual", commitment="certain", allegation="no", time_kind="none",
             time_basis="none", relation_to_earlier="none", literal_or_inferred="literal", representable="yes",
             expected_admission="formed", original_claimant_kind="")
    g.update(kw)
    return g


def month(expr, kind, earliest, latest):
    return dict(time_expression=expr, time_kind=kind, time_earliest=earliest, time_latest=latest,
                time_precision="month", time_basis="stated")


EMP = "employee=Ilse Varga | employer={}"
GOLD = [
    gold("S-01-a1", "S-01", "Ilse Varga joined Corvan Freight as general counsel in May 2025", "employment",
         EMP.format("Corvan Freight"), title="general counsel", **month("May 2025", "start", "2025-05-01", "2025-06-01")),
    gold("S-02-a1", "S-02", "Ilse Varga reports to Piet Marr", "reporting", "report=Ilse Varga | manager=Piet Marr",
         original_claimant="Tamsin Oduya", original_claimant_kind="person", attribution_mode="reported"),
    gold("S-03-a1", "S-03", "Ilse Varga left Corvan Freight in June 2025", "employment", EMP.format("Corvan Freight"),
         **month("June 2025", "end", "2025-06-01", "2025-07-01")),
    gold("S-04-a1", "S-04", "Ilse Varga left Corvan Freight in July 2025, not June", "employment", EMP.format("Corvan Freight"),
         relation_to_earlier="corrects", target_assertion_id="S-03-a1", expected_admission="review",
         **month("July 2025", "end", "2025-07-01", "2025-08-01")),
    gold("S-05-a1", "S-05", "Ilse Varga joined Brightmere in March 2025", "employment", EMP.format("Brightmere"),
         **month("March 2025", "start", "2025-03-01", "2025-04-01")),
    gold("S-06-a1", "S-06", "Ilse Varga joined Brightmere in February 2025", "employment", EMP.format("Brightmere"),
         **month("February 2025", "start", "2025-02-01", "2025-03-01")),
    gold("S-07-a1", "S-07", "Ilse Varga joined Brightmere in April 2025", "employment", EMP.format("Brightmere"),
         relation_to_earlier="corrects", target_assertion_id="?", expected_admission="review",
         **month("April 2025", "start", "2025-04-01", "2025-05-01")),
    gold("S-09-a1", "S-09", "Ilse Varga chairs the Corvan Freight audit panel", "statement",
         "subject=Ilse Varga | object=Corvan Freight audit panel", predicate="chairs", original_claimant="Hal Ostrow",
         original_claimant_kind="unknown", attribution_mode="forwarded", attribution_chain="Rui Banks | Hal Ostrow"),
    gold("S-10-a1", "S-10", "Ilse Varga chairs the Corvan Freight audit panel", "statement",
         "subject=Ilse Varga | object=Corvan Freight audit panel", predicate="chairs", original_claimant="Hal Ostrow",
         original_claimant_kind="unknown", attribution_mode="forwarded", attribution_chain="Wen Abara | Hal Ostrow",
         source_speaker="Wen Abara", independent_origin="no", relation_to_earlier="repeats", target_assertion_id="S-09-a1",
         expected_admission="withheld"),
]
CATEGORIES = {p["passage_id"]: {"categories": ["synthetic"], "negative_control": p["passage_id"] == "S-08"} for p in PASSAGES}


def assertion(evidence, participants, relation="employment", times=(), claimant=None, claimant_kind=None,
              mode="direct", **kw):
    a = {"evidence": evidence, "relation": relation,
         "participants": [{"role": r, "text": t, "kind": k, "is_pronoun_or_vague": False} for r, t, k in participants],
         "times": [{"text": t, "kind": k} for t, k in times], "polarity": "positive", "modality": "actual",
         "commitment": "certain", "attribution": {"mode": mode, "claimant": claimant, "claimant_kind": claimant_kind, "via": []},
         "basis": "explicit"}
    a.update(kw)
    return a


def response(*assertions, outcome="assertions"):
    return {"format": RESPONSE_FORMAT, "outcome": outcome, "assertions": list(assertions), "problems": []}


def emp(org):
    return [("employee", "Ilse Varga", "person"), ("employer", org, "organization")]


PANEL = [("subject", "Ilse Varga", "person"), ("object", "Corvan Freight audit panel", "unclassified")]
FWD_ASSERTION = assertion("Ilse Varga chairs the Corvan Freight audit panel", PANEL, relation="statement",
                          mode="forwarded", predicate="chairs")
CORRECT = {
    "S-01": response(assertion("Ilse Varga joined Corvan Freight as general counsel in May 2025", emp("Corvan Freight"),
                               times=[("May 2025", "start")], title="general counsel")),
    "S-02": response(assertion("Ilse Varga reports to Piet Marr", [("report", "Ilse Varga", "person"), ("manager", "Piet Marr", "person")],
                               relation="reporting", claimant="Tamsin Oduya", claimant_kind="person", mode="reported")),
    "S-03": response(assertion("Ilse Varga left Corvan Freight in June 2025", emp("Corvan Freight"), times=[("June 2025", "end")])),
    "S-04": response(assertion("Ilse Varga left Corvan Freight in July 2025, not June", emp("Corvan Freight"),
                               times=[("July 2025", "end")], correction={"kind": "corrects", "cue": "Correction:", "earlier_statement": None})),
    "S-05": response(assertion("Ilse Varga joined Brightmere in March 2025", emp("Brightmere"), times=[("March 2025", "start")])),
    "S-06": response(assertion("Ilse Varga joined Brightmere in February 2025", emp("Brightmere"), times=[("February 2025", "start")])),
    "S-07": response(assertion("Ilse Varga joined Brightmere in April 2025", emp("Brightmere"), times=[("April 2025", "start")],
                               correction={"kind": "corrects", "cue": "Scratch that:", "earlier_statement": None})),
    "S-08": response(outcome="no-relevant-assertion"),
    "S-09": response(FWD_ASSERTION),
    "S-10": response(FWD_ASSERTION),
}


def responses(**changes):
    """The correct responses as raw JSON text, with some replaced (a dict, or raw text as a model wrote it)."""
    out = copy.deepcopy(CORRECT)
    out.update(changes)
    return {k: v if isinstance(v, str) else json.dumps(v) for k, v in out.items()}


def write(tmp_path, raw=None, gold_rows=None, passages=None):
    """public/, private/ and responses/ directories under tmp_path, as the real evaluation lays them out."""
    pub, priv, resp = tmp_path / "public", tmp_path / "private", tmp_path / "responses"
    for d in (pub, priv, resp):
        d.mkdir()
    (pub / "passages.jsonl").write_text("".join(json.dumps(p) + "\n" for p in (passages or PASSAGES)))
    for name in ("response-format.md", "extraction-instructions.md", "README.md"):
        (pub / name).write_text(f"# {name}\n")
    (pub / "claude-settings.json").write_text('{"permissions": {"deny": ["Bash"]}}\n')
    (priv / "gold.jsonl").write_text("".join(json.dumps(g) + "\n" for g in (gold_rows or GOLD)))
    (priv / "categories.json").write_text(json.dumps(CATEGORIES))
    for pid, text in (raw if raw is not None else responses()).items():
        (resp / f"{pid}.json").write_text(text)
    return pub, priv, resp
