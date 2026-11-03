"""The extraction contract: what an extractor returns, and the validator that turns it into GUPI records.

An extractor returns JSON-like data for ONE observation:

    {"mentions": [{"id": "m1", "text": "Alice", "start": 0, "end": 5, "kind": "person"}, ...],
     "claims": [{"type": "reporting", "roles": {"report": ["m1"], "manager": ["m2"]},
                 "values": {}, "quote": "Alice reports to Bob", "start": 0, "end": 20,
                 "basis": "explicit", "confidence": 0.9,
                 "time": {"start": "March 2024", "end": null, "ongoing": true}}, ...]}

A generic claim uses "type": "statement" with "predicate" and optionally "object_text".

The validator never trusts the extractor. Mentions and quotes must match the source text exactly; claim
types, roles, player kinds and attributes must already exist in the schema (no schema evolution); time
phrases must appear in the text and are read by gupi.timeexpr, never taken as dates from the extractor.
Anything that fails is rejected with a reason, and the rest is kept. Nothing here accepts a claim.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from gupi import ids, migrations, timeexpr, typeql
from gupi.records import Claim, Evidence, Mention, Referent
from gupi.temporal import ValidTime

GENERIC = "statement"
UNCLASSIFIED = "unclassified"
CORE_CLAIM_ATTRIBUTES = {
    "gupi-id", "proposition-key", "time-precision", "valid-to-basis", "method", "extraction-basis",
    "predicate-text", "object-text",
}


@dataclass(frozen=True)
class SchemaInfo:
    """What the extractor may use, read from the live database."""

    referent_types: frozenset
    roles: dict          # claim type -> {role -> frozenset of referent types that may play it}
    attributes: dict     # claim type -> frozenset of string attributes it owns (beyond the core ones)
    mappings: dict = field(default_factory=dict)  # normalised predicate -> {"type", "subject", "object"}

    @classmethod
    def load(cls, tx, packs):
        roles, attributes = {}, {}
        for r in typeql.concept_rows(tx, "match $t sub claim; $t relates $r; $p plays $r; $p sub referent;"):
            t, role = r.get("t").get_label(), r.get("r").get_label().split(":", 1)[1]
            roles.setdefault(t, {}).setdefault(role, set()).add(r.get("p").get_label())
        for r in typeql.concept_rows(tx, "match $t sub claim; $t owns $a; $a value string;"):
            attributes.setdefault(r.get("t").get_label(), set()).add(r.get("a").get_label())
        referents = {r.get("t").get_label() for r in typeql.concept_rows(tx, "match $t sub referent;")}
        mappings = {}
        for pack in packs:
            path = migrations.BUILTIN / pack / "predicates.json"
            if path.exists():
                mappings.update({normalise(k): v for k, v in json.loads(path.read_text()).items() if not k.startswith("_")})
        return cls(
            referent_types=frozenset(referents - {"referent"}),
            roles={t: {role: frozenset(p) for role, p in rs.items()} for t, rs in roles.items()},
            attributes={t: frozenset(a - CORE_CLAIM_ATTRIBUTES) for t, a in attributes.items()},
            mappings=mappings,
        )

    def describe(self):
        """A plain description for prompts: typed claim types first, the generic one last."""
        lines = []
        for t in sorted(self.roles, key=lambda t: (t == GENERIC, t)):
            if t == "identity":
                continue  # identity decisions are Phase 3, not extraction output
            roles = ", ".join(f"{r} ({'/'.join(sorted(p))})" for r, p in sorted(self.roles[t].items()))
            attrs = ", ".join(sorted(self.attributes.get(t, ()))) or "none"
            lines.append(f"- {t}: roles {roles}; attributes {attrs}")
        return "\n".join(lines)


@dataclass
class Extraction:
    referents: list = field(default_factory=list)
    mentions: list = field(default_factory=list)
    claims: list = field(default_factory=list)
    rejected: list = field(default_factory=list)   # (what, reason)
    notes: list = field(default_factory=list)      # assumptions and conversions
    times: list = field(default_factory=list)      # per claim and bound: phrase, explicit or inferred, assumption

    def report(self):
        return {"mentions": len(self.mentions), "claims": len(self.claims),
                "rejected": [{"item": w, "reason": r} for w, r in self.rejected], "notes": self.notes,
                "times": self.times}


def normalise(text):
    return re.sub(r"\s+", " ", str(text).strip().casefold())


def referent_id(scope, kind, surface):
    """Referents are scoped to one conversation or document: no cross-source merging here (Phase 3)."""
    return ids.stable_id("ref", scope, kind, normalise(surface))


def _span(text, quote, start, end):
    """The (start, end) of `quote` in `text`: the given span if it matches, else its first occurrence.

    LLMs are unreliable at character offsets, so a quote without a valid span is located in the text; it must
    still appear there exactly.
    """
    if isinstance(start, int) and isinstance(end, int) and 0 <= start <= end <= len(text) and text[start:end] == quote:
        return start, end
    if quote and quote in text:
        i = text.index(quote)
        return i, i + len(quote)
    return None


def validate(raw, observation, schema: SchemaInfo, scope, method):
    """Check an extractor's output for one observation and build records from what passes."""
    out = Extraction()
    text = observation.content
    if not isinstance(raw, dict):
        out.rejected.append(("output", "extractor output is not an object"))
        return out

    by_mention = {}
    for m in raw.get("mentions") or []:
        if not isinstance(m, dict):
            out.rejected.append(("mention", "mention is not an object"))
            continue
        surface = m.get("text")
        span = _span(text, surface, m.get("start"), m.get("end")) if surface else None
        if not span:
            out.rejected.append((f"mention {surface!r}", "text does not match the source"))
            continue
        try:
            confidence = _confidence(m.get("confidence"))
        except ValueError as e:
            out.rejected.append((f"mention {surface!r}", str(e)))
            continue
        kind = m.get("kind")
        if kind not in schema.referent_types:
            out.notes.append(f"mention {surface!r}: kind {kind!r} is not in the schema; recorded as {UNCLASSIFIED}")
            kind = UNCLASSIFIED
        rid = referent_id(scope, kind, surface)
        ref = Referent(rid, kind, surface)
        if ref not in out.referents:
            out.referents.append(ref)
        out.mentions.append(Mention(observation.id, span[0], span[1], surface, rid, confidence, method))
        by_mention[m.get("id")] = (rid, kind)

    for i, c in enumerate(raw.get("claims") or []):
        try:
            out.claims.append(_claim(c, text, observation, schema, by_mention, method, out.notes, out.times))
        except ValueError as e:
            out.rejected.append((f"claim {i} ({c.get('type') if isinstance(c, dict) else '?'})", str(e)))
    return out


def _confidence(value):
    if value is None:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0.0 <= float(value) <= 1.0:
        raise ValueError("confidence must be a number between 0 and 1")
    return float(value)


def _claim(c, text, observation, schema, by_mention, method, notes, times=None):
    if not isinstance(c, dict):
        raise ValueError("claim is not an object")
    claim_type = c.get("type")
    if claim_type == "identity" or claim_type not in schema.roles:
        raise ValueError(f"claim type {claim_type!r} is not available for extraction")
    basis = c.get("basis")
    if basis not in ("explicit", "inferred"):
        raise ValueError("basis must be 'explicit' or 'inferred'")
    span = _span(text, c.get("quote"), c.get("start"), c.get("end"))
    if not span:
        raise ValueError("quote does not match the source text")

    roles = {}
    for role, mention_ids in (c.get("roles") or {}).items():
        allowed = schema.roles[claim_type].get(role)
        if allowed is None:
            raise ValueError(f"{claim_type} has no role {role!r}")
        for mid in [mention_ids] if isinstance(mention_ids, str) else mention_ids or []:
            if mid not in by_mention:
                raise ValueError(f"role {role!r} names an unknown or rejected mention {mid!r}")
            rid, kind = by_mention[mid]
            if kind not in allowed:
                raise ValueError(f"a {kind} cannot play {claim_type}:{role}")
            roles.setdefault(role, []).append(rid)
    if not roles:
        raise ValueError("a claim needs at least one role player")

    values = {}
    for attr, value in (c.get("values") or {}).items():
        if attr not in schema.attributes.get(claim_type, ()):
            raise ValueError(f"{claim_type} has no attribute {attr!r}")
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"attribute {attr!r} needs a non-empty text value")
        values[attr] = value.strip()

    if claim_type == GENERIC:
        predicate = normalise(c.get("predicate") or "")
        if not predicate:
            raise ValueError("a generic statement needs a predicate")
        if "subject" not in roles:
            raise ValueError("a generic statement needs a subject referent")
        mapped = schema.mappings.get(predicate)
        if mapped and len(roles.get("object", [])) == 1 and len(roles["subject"]) == 1 and not c.get("object_text"):
            notes.append(f"statement {predicate!r} converted to typed claim {mapped['type']}")
            claim_type = mapped["type"]
            roles = {mapped["subject"]: roles["subject"], mapped["object"]: roles["object"]}
            for role, refs in roles.items():
                kinds = {k for r, k in by_mention.values() if r in refs}
                if not kinds <= schema.roles[claim_type][role]:
                    raise ValueError(f"cannot convert {predicate!r}: a {kinds} cannot play {claim_type}:{role}")
        else:
            values["predicate-text"] = predicate
            if c.get("object_text"):
                values["object-text"] = str(c["object_text"]).strip()

    readings = []
    valid, precision, to_basis = _time(c.get("time") or {}, text, observation.observed_at, notes, readings)
    claim = Claim(
        claim_type, {r: tuple(v) if len(v) > 1 else v[0] for r, v in roles.items()},
        evidence=(Evidence(observation.id, *span),), valid=valid, values=values,
        time_precision=precision, valid_to_basis=to_basis, method=method,
        confidence=_confidence(c.get("confidence")), basis=basis,
    )
    if times is not None:
        times += [{"claim": claim.id, **r} for r in readings]
    return claim


def _time(t, text, observed_at, notes, readings_out=None):
    readings = {}
    for side in ("start", "end"):
        phrase = t.get(side)
        if not phrase:
            continue
        if normalise(phrase) not in normalise(text):
            notes.append(f"time phrase {phrase!r} is not in the source text; {side} left unknown")
            continue
        found = re.search(r"\s+".join(map(re.escape, phrase.split())), text, re.I)  # position in the original text
        reading = timeexpr.read(phrase, observed_at, timeexpr.direction(text, found.start() if found else None))
        if reading is None:
            notes.append(f"time phrase {phrase!r} could not be read, or its year is ambiguous; {side} left unknown")
            if readings_out is not None:
                readings_out.append({"bound": side, "phrase": phrase, "read": False})
            continue
        if reading.assumption:
            notes.append(f"{phrase!r}: {reading.assumption}")
        if readings_out is not None:
            readings_out.append({"bound": side, "phrase": phrase, "read": True, "explicit": reading.explicit,
                                 "assumption": reading.assumption})
        readings[side] = reading
    start, end = readings.get("start"), readings.get("end")
    vt = ValidTime(start and start.earliest, start and start.latest, end and end.earliest, end and end.latest)
    if end:
        to_basis = "stated"
    elif t.get("ongoing") is True and observed_at is not None:
        vt = ValidTime(vt.from_earliest, vt.from_latest, to_earliest=observed_at)
        to_basis = "ongoing-at-observation"
    else:
        to_basis = "unknown"
    return vt, timeexpr.coarsest(start and start.precision, end and end.precision), to_basis
