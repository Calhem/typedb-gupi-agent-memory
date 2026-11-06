"""Structural validation of memory candidates, and the provisional mapping of their time evidence onto a
claim's valid time (docs/formation/candidate-ir.md §4-§5).

Validation never repairs anything. It returns every problem found, and an empty list means the set is
structurally sound. Sound is not the same as true or accepted: candidates stay separate from memory.
"""

import re
from dataclasses import dataclass

from gupi import ids
from gupi.formation.candidate import (
    ATTRIBUTION_MODES, BASES, CLAIMANT_KINDS, COMMITMENTS, EVENT_TYPE, IR_VERSION, IR_VERSION_1_1, IR_VERSIONS, MODALITIES,
    NULLABLE_TARGET_KINDS, POLARITIES, PRECISIONS, RELATION_KINDS, TIME_KINDS, TRANSMISSION,
)
from gupi.temporal import ValidTime

LABEL = re.compile(r"^[a-z][a-z0-9-]*$")
# A generic statement carries its predicate and object text as candidate values (candidate-ir.md); the
# extraction contract's SchemaInfo.attributes leaves these core attributes out, so they are checked against
# what the type really owns (SchemaInfo.owned).
STATEMENT_VALUES = ("predicate-text", "object-text")
GENERIC_TYPES = ("statement", EVENT_TYPE)
# Attributes formation sets from the candidate's own fields: never supplied as values.
SET_BY_FORMATION = frozenset({"polarity", "commitment", "attribution-mode", "candidate-id", "valid-from-basis",
                              "reason", "gupi-id", "proposition-key", "time-precision", "valid-to-basis", "method",
                              "extraction-basis", "occurred-at-basis"})
SINCE_BEFORE = re.compile(r"\b(?:ever )?since\s+$", re.I)


@dataclass(frozen=True)
class Issue:
    where: str                      # "set", or "candidate <n>"
    code: str
    message: str


def validate(cset, observation, schema=None):
    """Problems with `cset` (a CandidateSet) for `observation` (a gupi.records.Observation).

    `schema` (optional, a gupi.extraction.contract.SchemaInfo) adds checks of claim types, roles, player
    kinds and attributes against the live schema."""
    issues = []
    text = observation.content

    def bad(where, code, message):
        issues.append(Issue(where, code, message))

    if cset.ir_version not in IR_VERSIONS:
        bad("set", "version", f"ir_version {cset.ir_version!r} is not one of {', '.join(IR_VERSIONS)}")
    if cset.observation_id != observation.id:
        bad("set", "observation", "observation_id does not match the observation")
    if cset.content_hash != ids.content_hash(text):
        bad("set", "content-hash", "content_hash does not match the observation's content")
    if not cset.extractor:
        bad("set", "extractor", "the extractor method is required")

    known = [c.id for c in cset.candidates]
    for dup in sorted({i for i in known if known.count(i) > 1}):
        bad("set", "duplicate", f"candidate {dup} appears more than once")
    for n, c in enumerate(cset.candidates):
        _candidate(c, f"candidate {n}", text, observation.id, set(known), schema, bad)
        _version_1_1(c, f"candidate {n}", cset.ir_version, text, bad)
    return issues  # relations cannot form cycles: a candidate's id includes its relations' targets


def _candidate(c, where, text, observation_id, known, schema, bad):
    p = c.passage
    if p.observation_id != observation_id:
        bad(where, "passage", "passage is from a different observation")
    if not _within(p.start, p.end, 0, len(text)) or text[p.start:p.end] != p.text:
        bad(where, "passage", "passage text does not match the observation at its offsets")
    if not LABEL.match(c.claim_type or ""):
        bad(where, "claim-type", f"claim type {c.claim_type!r} is not a valid label")
    if not c.participants:
        bad(where, "participants", "a candidate needs at least one participant")
    for p_ in c.participants:
        if not LABEL.match(p_.role or ""):
            bad(where, "role", f"role {p_.role!r} is not a valid label")
        if not _within(p_.start, p_.end, p.start, p.end) or text[p_.start:p_.end] != p_.surface:
            bad(where, "participant", f"participant {p_.surface!r} does not match the passage at its offsets")
    for attr, value in c.values:
        if not LABEL.match(attr) or not isinstance(value, str) or not value.strip():
            bad(where, "value", f"value {attr!r} needs a label and non-empty text")
        elif attr in SET_BY_FORMATION:
            bad(where, "value", f"{attr!r} is set by formation from the candidate's own fields, not given as a value")
        elif attr in STATEMENT_VALUES and c.claim_type not in GENERIC_TYPES:
            bad(where, "value", f"{attr!r} belongs to a generic statement, not to {c.claim_type!r}")
    if c.claim_type in GENERIC_TYPES:
        _statement(c, where, bad)
    _enum(where, "polarity", c.polarity, POLARITIES, bad)
    _enum(where, "modality", c.modality, MODALITIES, bad)
    _enum(where, "commitment", c.commitment, COMMITMENTS, bad)
    _enum(where, "basis", c.basis, BASES, bad)
    _enum(where, "attribution", c.attribution.mode, ATTRIBUTION_MODES, bad)
    for t in c.attribution.transmission:
        _enum(where, "transmission", t, TRANSMISSION, bad)
    if c.confidence is not None and not (isinstance(c.confidence, float) and 0.0 <= c.confidence <= 1.0):
        bad(where, "confidence", "confidence must be a number between 0 and 1")
    _times(c, where, text, bad)
    for r in c.relations:
        _enum(where, "relation", r.kind, RELATION_KINDS, bad)
        _enum(where, "relation-marked", r.marked, ("stated", "inferred"), bad)
        if r.target is None:
            continue  # a null target: checked by _version_1_1
        if r.target == c.id:
            bad(where, "relation", "a candidate cannot relate to itself")
        elif r.target not in known and not r.target.startswith(("claim:", "candidate:")):
            bad(where, "relation", f"relation target {r.target!r} is neither a candidate nor a claim id")
    if schema is not None:
        _schema(c, where, schema, bad)


def _version_1_1(c, where, version, text, bad):
    """The 1.1 fields: allowed only in a 1.1 set, each with its own rule."""
    kind, null_targets = c.attribution.asserted_by_kind, [r for r in c.relations if r.target is None]
    if version != IR_VERSION_1_1 and (kind is not None or null_targets):
        bad(where, "version", f"asserted_by_kind and null relation targets need {IR_VERSION_1_1}")
    if kind is not None:
        if kind not in CLAIMANT_KINDS:
            bad(where, "attribution", f"asserted_by_kind {kind!r} is not one of {', '.join(CLAIMANT_KINDS)}")
        if c.attribution.asserted_by is None:
            bad(where, "attribution", "asserted_by_kind without a claimant (asserted_by)")
    if version == IR_VERSION_1_1 and c.attribution.asserted_by is not None and c.attribution.asserted_by not in text:
        bad(where, "attribution", f"claimant {c.attribution.asserted_by!r} does not occur in the observation")
    for r in null_targets:
        if r.kind not in NULLABLE_TARGET_KINDS:
            bad(where, "relation", f"only {', '.join(NULLABLE_TARGET_KINDS)} may have an unresolved (null) target")


def _times(c, where, text, bad):
    kinds = [t.kind for t in c.times]
    for k in ("start", "end", "holds-since"):
        if kinds.count(k) > 1:
            bad(where, "time", f"more than one {k!r} time")
    for t in c.times:
        _enum(where, "time-kind", t.kind, TIME_KINDS, bad)
        _enum(where, "precision", t.precision, PRECISIONS, bad)
        if not _within(t.start, t.end, c.passage.start, c.passage.end) or text[t.start:t.end] != t.phrase:
            bad(where, "time", f"time phrase {t.phrase!r} does not match the passage at its offsets")
        if t.earliest is None and t.latest is None and t.precision != "unknown":
            bad(where, "time", f"time phrase {t.phrase!r} has no window (allowed only with precision 'unknown')")
        if t.earliest is not None and t.latest is not None and t.earliest > t.latest:
            bad(where, "time", f"time phrase {t.phrase!r} has its window the wrong way round")
        if t.kind == "start" and SINCE_BEFORE.search(text[max(0, t.start - 12):t.start]):
            bad(where, "since-as-start", f"{t.phrase!r} follows 'since': that is lower-bound evidence of "
                                         "continuity (holds-since), not a stated start")
    start = next((t for t in c.times if t.kind == "start"), None)
    end = next((t for t in c.times if t.kind == "end"), None)
    if start and end and start.earliest and end.latest and start.earliest >= end.latest:
        bad(where, "time", "the start window lies entirely after the end window")


def _schema(c, where, schema, bad):
    if c.claim_type == "identity" or c.claim_type not in schema.roles:
        bad(where, "schema", f"claim type {c.claim_type!r} is not available for extraction")
        return
    roles = schema.roles[c.claim_type]
    for p in c.participants:
        if p.role not in roles:
            bad(where, "schema", f"{c.claim_type} has no role {p.role!r}")
        elif p.kind not in roles[p.role]:
            bad(where, "schema", f"a {p.kind} cannot play {c.claim_type}:{p.role}")
    owned = set(schema.attributes.get(c.claim_type, ()))
    if c.claim_type in GENERIC_TYPES:
        owned |= set(STATEMENT_VALUES) & set(schema.owned.get(c.claim_type, ()))
    for attr, _ in c.values:
        if attr not in owned and attr not in SET_BY_FORMATION:
            bad(where, "schema", f"{c.claim_type} has no attribute {attr!r}")


def _statement(c, where, bad):
    """A generic statement: one subject or more, exactly one predicate, an object participant or object text
    (or neither: "Kim retired"), and nothing else."""
    roles = {p.role for p in c.participants}
    predicates = [v for a, v in c.values if a == "predicate-text"]
    if "subject" not in roles:
        bad(where, "statement", "a generic statement needs a subject")
    if len(predicates) != 1:
        bad(where, "statement", f"a generic statement needs exactly one predicate-text (has {len(predicates)})")
    if sum(a == "object-text" for a, _ in c.values) > 1:
        bad(where, "statement", "a generic statement has at most one object-text")


def _enum(where, name, value, allowed, bad):
    if value not in allowed:
        bad(where, name, f"{name} {value!r} is not one of {', '.join(allowed)}")


def _within(start, end, lo, hi):
    return isinstance(start, int) and isinstance(end, int) and lo <= start <= end <= hi


# --- provisional mapping onto a claim's valid time (not used by ingestion in 6A) ------------------------

class Unmappable(ValueError):
    pass


def occurrence(candidate):
    """(earliest, latest, basis, precision) of a one-time event: when it happened, which is not when it was said. All
    None for an event stated with no date: none is ever supplied. Basis is "stated", or "derived" when the date was read
    from the message's own time."""
    if len(candidate.times) > 1 or any(t.kind != "holds-at" for t in candidate.times):
        raise Unmappable("an event happens at one stated time, so a start, end, span or second time is a state's")
    if not candidate.times or candidate.times[0].earliest is None:
        return None, None, None, None
    t = candidate.times[0]
    return t.earliest, t.latest, "stated" if t.explicit else "derived", t.precision


def valid_time(candidate):
    """(ValidTime, valid-to-basis) for a candidate's time evidence, per candidate-ir.md §5.

    - start [e, l): from-earliest e, from-latest l
    - end [e, l): to-earliest e, to-latest l
    - holds-since [e, l): from-latest l only, or the statement's own instant if that is earlier ("since June",
      said on 10 June). The state certainly held from then; when it began is NOT stated, so from-earliest stays
      open. This is never mapped to a start.
    - holds-at an instant o: to-earliest o, basis "ongoing-at-observation" when there is no end
    A holds-at over a coarser window ("was CTO in March") says only that it held at some instant in it, which
    a valid time cannot express: Unmappable.
    """
    if candidate.claim_type == EVENT_TYPE:
        occurrence(candidate)                  # raises if it has no single occurrence; an event never has a valid time
        return ValidTime(), None
    by = {t.kind: t for t in candidate.times if t.earliest is not None or t.latest is not None}  # unread: no bound
    fe = fl = te = tl = None
    basis = "unknown"
    if "start" in by and "holds-since" in by:
        fe, fl = by["start"].earliest, min(by["start"].latest, by["holds-since"].latest)
    elif "start" in by:
        fe, fl = by["start"].earliest, by["start"].latest
    elif "holds-since" in by:
        fl = by["holds-since"].latest
    if "holds-since" in by:
        # "since June", said on 10 June while it holds: it certainly began by the moment it was said
        now = [t.earliest for t in candidate.times if t.kind == "holds-at" and t.earliest == t.latest and t.earliest]
        if now and fl is not None:
            fl = min(fl, min(now))
    if "end" in by:
        te, tl, basis = by["end"].earliest, by["end"].latest, "stated"
    held = [t for t in candidate.times if t.kind == "holds-at" and t.earliest is not None]
    for t in held:
        if t.earliest != t.latest:
            raise Unmappable(f"{t.phrase!r} says only that it held at some instant in a window")
        if "end" not in by:
            te, basis = t.earliest if te is None else max(te, t.earliest), "ongoing-at-observation"
    return ValidTime(fe, fl, te, tl), basis
