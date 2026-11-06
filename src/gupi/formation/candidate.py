"""Memory candidates: the versioned intermediate representation between an extractor and memory
(docs/formation/candidate-ir.md).

A candidate is what an extractor thinks one passage of one observation says. It keeps what claims cannot yet
hold:
- the exact passage
- who asserted it and how it reached the source
- participants as written, with their roles
- each time phrase, with its kind and precision
- modality, the source's commitment and polarity
- the extractor's confidence
- correction relationships

Candidates are not memory. Nothing here reads or writes TypeDB, and a candidate never becomes a claim in
Phase 6A.
"""

from dataclasses import dataclass, field
from datetime import datetime

from gupi import ids

IR_VERSION = "gupi.candidate/1"
IR_VERSION_1_1 = "gupi.candidate/1.1"   # adds asserted_by_kind and null correction targets (additive)
IR_VERSIONS = (IR_VERSION, IR_VERSION_1_1)
CLAIMANT_KINDS = ("person", "organisation", "unknown")
EVENT_TYPE = "event-statement"          # a one-time event (core/0013): shaped like a statement, but it never "holds"
NULLABLE_TARGET_KINDS = ("corrects", "retracts", "updates")

TIME_KINDS = {
    "start": "the state began inside the window (\"joined in March\")",
    "end": "the state ended inside the window (\"left in May\")",
    "holds-since": "the state held from the window, or earlier, until the statement's time "
                   "(\"has worked here since March\"): lower-bound continuity, not a start",
    "holds-at": "the state held at some instant in the window (\"is CTO\" at the observation; \"was CTO in March\")",
}
PRECISIONS = ("instant", "day", "month", "year", "unknown")
POLARITIES = ("positive", "negative")
MODALITIES = ("actual", "planned", "required", "permitted", "requested", "conditional", "hypothetical", "question")
COMMITMENTS = ("certain", "probable", "possible", "unknown")
ATTRIBUTION_MODES = ("direct", "reported", "quoted", "forwarded", "rumour", "unattributed")
TRANSMISSION = ("forwarded", "transcribed", "paraphrased", "excerpted", "authenticity-unclear")
RELATION_KINDS = ("corrects", "retracts", "updates", "repeats", "resumes", "contradicts")
BASES = ("explicit", "inferred")


@dataclass(frozen=True)
class Passage:
    """The exact source text the candidate rests on: `text` must equal the observation's content[start:end]."""

    observation_id: str
    start: int
    end: int
    text: str


@dataclass(frozen=True)
class Participant:
    """A role player as written in the passage. Resolution to a referent happens later, not here."""

    role: str
    surface: str
    start: int
    end: int
    kind: str                      # referent type, e.g. "person"


@dataclass(frozen=True)
class TimeEvidence:
    """One time phrase and what it says about the state. The window is what `gupi.timeexpr` read."""

    kind: str                      # one of TIME_KINDS
    phrase: str
    start: int
    end: int
    earliest: datetime | None
    latest: datetime | None
    precision: str = "unknown"
    explicit: bool = True          # False when the year or date was inferred (e.g. from tense)
    assumption: str | None = None


@dataclass(frozen=True)
class Attribution:
    """Who made the assertion, and how it reached the source (guidelines §8, §8.2)."""

    asserted_by: str | None = None  # a participant surface or referent id; None: the observation's author
    mode: str = "direct"
    via: tuple = ()                 # intermediaries, nearest first
    transmission: tuple = ()
    asserted_by_kind: str | None = None  # 1.1: person | organisation | unknown; None: not established


@dataclass(frozen=True)
class Relation:
    """How this candidate bears on another candidate in its set, or on an existing claim ("claim:...")."""

    kind: str
    target: str | None              # 1.1: None for a stated correction whose target is not established
    marked: str = "stated"          # "stated" (the text says so, e.g. "Correction:") or "inferred"
    cue: str | None = None


@dataclass(frozen=True)
class Candidate:
    claim_type: str
    passage: Passage
    participants: tuple
    values: tuple = ()              # (attribute, text value) pairs, sorted
    times: tuple = ()
    polarity: str = "positive"
    modality: str = "actual"
    commitment: str = "certain"     # the source's commitment, not the extractor's
    attribution: Attribution = field(default_factory=Attribution)
    relations: tuple = ()
    basis: str = "explicit"
    confidence: float | None = None  # the extractor's own confidence

    @property
    def id(self):
        return ids.stable_id("candidate", IR_VERSION, _plain(self))


@dataclass(frozen=True)
class CandidateSet:
    """Everything one extractor proposed for one observation."""

    observation_id: str
    content_hash: str
    extractor: str                  # method, e.g. "rules:v2"
    candidates: tuple = ()
    ir_version: str = IR_VERSION


def not_an_event(claim_type):
    """An event happened; it does not hold. Asking if it held at a time would turn a moment into a state."""
    if claim_type == EVENT_TYPE:
        raise ValueError("an event has no holding period: use Memory.events")


# --- serialisation -------------------------------------------------------------------------------------

def to_dict(cset):
    return {"ir_version": cset.ir_version, "observation_id": cset.observation_id,
            "content_hash": cset.content_hash, "extractor": cset.extractor,
            "candidates": [dict(_plain(c), id=c.id) for c in cset.candidates]}


def from_dict(d):
    """The inverse of to_dict. Structure only: call validate() before trusting it."""
    def times(ts):
        return tuple(TimeEvidence(t["kind"], t["phrase"], t["start"], t["end"], _dt(t.get("earliest")),
                                  _dt(t.get("latest")), t.get("precision", "unknown"), t.get("explicit", True),
                                  t.get("assumption")) for t in ts)

    def candidate(c):
        a = c.get("attribution") or {}
        return Candidate(
            c["claim_type"], Passage(**c["passage"]), tuple(Participant(**p) for p in c["participants"]),
            tuple(tuple(v) for v in c.get("values", ())), times(c.get("times", ())), c.get("polarity", "positive"),
            c.get("modality", "actual"), c.get("commitment", "certain"),
            Attribution(a.get("asserted_by"), a.get("mode", "direct"), tuple(a.get("via", ())),
                        tuple(a.get("transmission", ())), a.get("asserted_by_kind")),
            tuple(Relation(**r) for r in c.get("relations", ())), c.get("basis", "explicit"), c.get("confidence"))
    return CandidateSet(d["observation_id"], d["content_hash"], d["extractor"],
                        tuple(candidate(c) for c in d.get("candidates", ())), d.get("ir_version"))


def _plain(c):
    return {
        "claim_type": c.claim_type,
        "passage": vars(c.passage),
        "participants": [vars(p) for p in c.participants],
        "values": [list(v) for v in c.values],
        "times": [{**vars(t), "earliest": _iso(t.earliest), "latest": _iso(t.latest)} for t in c.times],
        "polarity": c.polarity, "modality": c.modality, "commitment": c.commitment,
        "attribution": {"asserted_by": c.attribution.asserted_by, "mode": c.attribution.mode,
                        "via": list(c.attribution.via), "transmission": list(c.attribution.transmission),
                        # 1.1 only, and only when set, so a 1.0 candidate's id is unchanged
                        **({"asserted_by_kind": c.attribution.asserted_by_kind}
                           if c.attribution.asserted_by_kind is not None else {})},
        "relations": [vars(r) for r in c.relations],
        "basis": c.basis, "confidence": c.confidence,
    }


def _iso(t):
    return t.isoformat() if t is not None else None


def _dt(s):
    return datetime.fromisoformat(s) if s else None
