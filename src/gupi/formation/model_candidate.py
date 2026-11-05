"""`model:candidate-v1`: turns recorded, model-shaped responses into `gupi.candidate/1` candidates, offline
(docs/evaluation/phase-7b/offline-extractor-interface.md). It never calls a model: a caller supplies the
response (a dict, or the raw JSON text a model would return).

The model may only *read*: which relation, which words, which modality. Code does everything authoritative:
- every quoted string is located exactly in the observation, and every offset is computed here
- time phrases are read by `gupi.timeexpr` (the model never supplies a date)
- forwarded text is detected from the message's own forward markers, not from the model's say-so
- participant identity is never resolved: a pronoun or vague reference stops the assertion
- correction targets are resolved here against earlier candidates in the thread, or the assertion stops

Anything that cannot be done safely produces an explicit outcome instead of a candidate. Outcomes are the
extractor's; validation and formation decisions come later and are separate.
"""

import json
import re
from dataclasses import dataclass, field

from gupi import ids, timeexpr
from gupi.formation import rules_v2
from gupi.formation.candidate import (
    ATTRIBUTION_MODES, COMMITMENTS, IR_VERSION_1_1, MODALITIES, NULLABLE_TARGET_KINDS, POLARITIES, Attribution,
    Candidate, CandidateSet, Participant, Passage, Relation, TimeEvidence,
)
from gupi.formation.rules_v21 import PRONOUNS
from gupi.formation.validate import validate

METHOD = "model:candidate-v1.1"          # emits gupi.candidate/1.1 (Stage 2B)
RESPONSE_FORMAT = "gupi.model-response/1.1"
RESPONSE_FORMATS = ("gupi.model-response/1", RESPONSE_FORMAT)   # format 1 recordings stay readable
RELATIONS = ("employment", "reporting", "statement")
KINDS = ("person", "organization", "unclassified")          # participant kinds (referent types)
CLAIMANT_KINDS = {"gupi.model-response/1": {"person": "person", "organization": "organisation", "unclassified": "unknown"},
                  "gupi.model-response/1.1": {"person": "person", "organisation": "organisation", "unknown": "unknown"}}
TIME_KINDS = ("start", "end", "holds-since", "holds-at")
CORRECTIONS = ("corrects", "retracts", "updates", "contradicts")
PROBLEM_KINDS = ("unsupported-domain", "ambiguous-reference", "insufficient-evidence")
LOWER_PRONOUNS = {p.lower() for p in PRONOUNS} | {"i", "me", "my"}
OUTCOMES = (
    "no-relevant-assertion",       # the model found nothing (correct for negative controls)
    "invalid-model-output",        # not JSON, wrong format, unknown or missing fields, bad values
    "grounding-failure",           # a quoted string is not in the message (or not inside the evidence)
    "ambiguous-span",              # a quoted string occurs more than once and no occurrence selects one
    "ambiguous-reference",         # a pronoun, vague reference or unknown author where a participant is needed
    "correction-target-unresolved",     # a "contradicts" with no single resolvable target (cannot be null)
    "inferred-not-admissible",     # the model says it inferred the assertion: no route to review exists
    "cue-conflict",                # the evidence contradicts the model's polarity or modality
    "unsupported-domain",          # reported by the model
    "insufficient-evidence",       # reported by the model
    "validation",                  # the candidate failed gupi.formation.validate
    "bare-retraction-unrecorded",  # R2: a retraction GUPI could not turn into a reviewable candidate (no author)
)
FLAGS = ("unreadable-time", "commitment-downgraded", "mode-forced-forwarded", "forwarded-unmarked",
         "predicate-paraphrased", "allegation", "correction-target-unresolved",
         "bare-retraction", "retraction-possible-targets", "allegation-context", "allegation-inherited")

HEDGE = re.compile(r"\b(?:probably|possibly|perhaps|maybe|might|could|apparently|reportedly|allegedly|"
                   r"supposedly|rumou?red|I think|I believe|it seems|likely|unconfirmed|not official)\b", re.I)
NEGATION = re.compile(r"\b(?:not|no longer|never|denie[sd]|deny|isn't|wasn't|doesn't|didn't|hasn't|won't|"
                      r"aren't|weren't)\b", re.I)
PRESENT = re.compile(r"(?:is|are|am|works?|reports?|leads?|owns?|manages?|heads?|runs?|chairs?|"
                     r"has (?:worked|been|reported|led|run|owned)|have (?:worked|been)|is (?:still|now) \w+|"
                     r"(?:still|now|currently) \w+|no longer \w+|does not \w+|doesn't \w+|is not|isn't)", re.I)
CONTRAST = re.compile(r",\s*not\s+[^,.;!?]+")   # a contrast (", not March"), never a plain "does not"
FUTURE_OR_CONDITIONAL = re.compile(r"\b(?:will|would|shall|plans? to|planning to|going to|intends? to|if|unless|"
                                   r"expected to|due to (?:join|leave|start))\b", re.I)

# R2: a retraction that does not restate what it retracts ("ignore what I said yesterday about Kim"); read by
# code from the message itself, whatever the model returned
BARE_RETRACTION = re.compile(
    r"\b(?:(?:please\s+)?(?:ignore|disregard|forget)\s+(?:what\s+I\s+(?:said|wrote|told\s+you|mentioned)|"
    r"my\s+(?:last|earlier|previous)\s+(?:message|email|note|post|comment))|"
    r"I\s+(?:retract|withdraw)\s+(?:that|what\s+I\s+said|my\s+(?:last|earlier|previous)\s+\w+)|"
    r"I\s+take\s+(?:that|it)\s+back|scratch\s+that|I\s+was\s+wrong\s+about|"
    r"I\s+mixed\s+(?:him|her|them|it|that)\s+up)\b", re.I)
NOT_BEFORE = re.compile(r"\b(?:don't|do not|never|didn't|did not)\s*$", re.I)
SENTENCE_END = re.compile(r"[.!?\n]")

TOP = {"format", "outcome", "assertions", "problems"}
ASSERTION_REQUIRED = {"evidence", "relation", "participants", "times", "polarity", "modality", "commitment",
                      "attribution", "basis"}
ASSERTION_OPTIONAL = {"evidence_occurrence", "predicate", "object_text", "title", "correction", "allegation"}
PARTICIPANT_KEYS = {"role", "text", "kind", "is_pronoun_or_vague"}
TIME_KEYS = {"text", "kind"}
ATTRIBUTION_KEYS = {"mode", "claimant", "claimant_kind", "via"}
CORRECTION_KEYS = {"kind", "cue", "earlier_statement"}
PROBLEM_KEYS = {"kind", "evidence", "detail"}


@dataclass
class Report:
    """What the extractor did not turn into candidates, and why; plus flags on candidates it did produce."""

    outcomes: list = field(default_factory=list)   # {"kind", "assertion", "evidence", "detail"}
    flags: list = field(default_factory=list)      # {"kind", "assertion", "detail"}

    @property
    def rejected(self):  # the rules:v2 shape: (text, reason)
        return [(o.get("evidence") or "", f"{o['kind']}: {o['detail']}") for o in self.outcomes]


class ResponseError(ValueError):
    pass


class ModelCandidateV1:
    """`responses` maps an observation id (or record key) to the recorded response for it."""

    method = METHOD

    def __init__(self, responses=None, source="recorded"):
        self.responses = dict(responses or {})
        self.source = source

    def extract(self, observation, prior=(), schema=None, response=None):
        report = Report()
        cset = CandidateSet(observation.id, ids.content_hash(observation.content), f"{METHOD}:{self.source}", (),
                            IR_VERSION_1_1)
        if response is None:
            response = self.responses.get(observation.id, self.responses.get(observation.record_key))
        try:
            data = _parse(response)
        except ResponseError as e:
            report.outcomes.append({"kind": "invalid-model-output", "assertion": None, "evidence": None, "detail": str(e)})
            return cset, report
        for p in data.get("problems", []):
            report.outcomes.append({"kind": p["kind"], "assertion": None, "evidence": p.get("evidence"),
                                    "detail": p.get("detail") or "reported by the model"})
        if data["outcome"] == "no-relevant-assertion":
            report.outcomes.append({"kind": "no-relevant-assertion", "assertion": None, "evidence": None,
                                    "detail": "the model found no relevant assertion"})
        earlier = [c for s in prior for c in s.candidates]
        made = []
        for n, a in enumerate(data["assertions"]):
            try:
                c = _candidate(a, n, observation, earlier + made, report, data["format"])
            except _Stop as stop:
                report.outcomes.append({"kind": stop.kind, "assertion": n, "evidence": a.get("evidence"),
                                        "detail": stop.detail})
                continue
            made.append(c)
        made += _bare_retractions(observation, made, earlier, report)
        kept = []
        for c in dict.fromkeys(made):
            issues = validate(CandidateSet(cset.observation_id, cset.content_hash, cset.extractor, (c,), IR_VERSION_1_1),
                              observation, schema)
            if issues:
                report.outcomes.append({"kind": "validation", "assertion": made.index(c), "evidence": c.passage.text,
                                        "detail": "; ".join(f"{i.code}: {i.message}" for i in issues)})
            else:
                kept.append(c)
        return CandidateSet(cset.observation_id, cset.content_hash, cset.extractor, tuple(kept), IR_VERSION_1_1), report


# --- parsing: the response format, strictly -----------------------------------------------------------

def _parse(response):
    if response is None:
        raise ResponseError("no recorded response for this observation")
    if isinstance(response, (str, bytes)):
        try:
            response = json.loads(response)
        except ValueError as e:
            raise ResponseError(f"not JSON: {e}") from None
    if not isinstance(response, dict):
        raise ResponseError("the response must be a JSON object")
    _keys(response, TOP, TOP, "response")
    if response["format"] not in RESPONSE_FORMATS:
        raise ResponseError(f"format must be one of {', '.join(RESPONSE_FORMATS)}")
    if response["outcome"] not in ("assertions", "no-relevant-assertion"):
        raise ResponseError("outcome must be 'assertions' or 'no-relevant-assertion'")
    if not isinstance(response["assertions"], list) or not isinstance(response["problems"], list):
        raise ResponseError("assertions and problems must be lists")
    if response["outcome"] == "no-relevant-assertion" and response["assertions"]:
        raise ResponseError("outcome 'no-relevant-assertion' with assertions")
    for p in response["problems"]:
        _keys(p, PROBLEM_KEYS, {"kind"}, "problem")
        _enum(p["kind"], PROBLEM_KINDS, "problem kind")
    for n, a in enumerate(response["assertions"]):
        where = f"assertion {n}"
        _keys(a, ASSERTION_REQUIRED | ASSERTION_OPTIONAL, ASSERTION_REQUIRED, where)
        _text(a["evidence"], f"{where} evidence")
        _enum(a["relation"], RELATIONS, f"{where} relation")
        _enum(a["polarity"], POLARITIES, f"{where} polarity")
        _enum(a["modality"], MODALITIES, f"{where} modality")
        _enum(a["commitment"], COMMITMENTS, f"{where} commitment")
        _enum(a["basis"], ("explicit", "inferred"), f"{where} basis")
        if "evidence_occurrence" in a and not (isinstance(a["evidence_occurrence"], int) and a["evidence_occurrence"] >= 1):
            raise ResponseError(f"{where}: evidence_occurrence must be a positive integer")
        for k in ("predicate", "object_text", "title"):
            if a.get(k) is not None:
                _text(a[k], f"{where} {k}")
        if "allegation" in a and not isinstance(a["allegation"], bool):
            raise ResponseError(f"{where}: allegation must be true or false")
        if not isinstance(a["participants"], list) or not a["participants"]:
            raise ResponseError(f"{where}: participants must be a non-empty list")
        for p in a["participants"]:
            _keys(p, PARTICIPANT_KEYS, PARTICIPANT_KEYS, f"{where} participant")
            _label(p["role"], f"{where} role")
            _text(p["text"], f"{where} participant text")
            _enum(p["kind"], KINDS, f"{where} participant kind")
            if not isinstance(p["is_pronoun_or_vague"], bool):
                raise ResponseError(f"{where}: is_pronoun_or_vague must be true or false")
        if not isinstance(a["times"], list):
            raise ResponseError(f"{where}: times must be a list")
        for t in a["times"]:
            _keys(t, TIME_KEYS, TIME_KEYS, f"{where} time")
            _text(t["text"], f"{where} time text")
            _enum(t["kind"], TIME_KINDS, f"{where} time kind")
        at = a["attribution"]
        _keys(at, ATTRIBUTION_KEYS, ATTRIBUTION_KEYS, f"{where} attribution")
        _enum(at["mode"], ATTRIBUTION_MODES, f"{where} attribution mode")
        if at["claimant"] is not None:
            _text(at["claimant"], f"{where} claimant")
            _enum(at["claimant_kind"], tuple(CLAIMANT_KINDS[response["format"]]), f"{where} claimant_kind")
        elif at["claimant_kind"] is not None:
            raise ResponseError(f"{where}: claimant_kind without a claimant")
        if not isinstance(at["via"], list) or not all(isinstance(v, str) and v.strip() for v in at["via"]):
            raise ResponseError(f"{where}: via must be a list of non-empty strings")
        if a.get("correction") is not None:
            corr = a["correction"]
            _keys(corr, CORRECTION_KEYS, {"kind", "cue"}, f"{where} correction")
            _enum(corr["kind"], CORRECTIONS, f"{where} correction kind")
            _text(corr["cue"], f"{where} correction cue")
    return response


def _keys(obj, allowed, required, where):
    if not isinstance(obj, dict):
        raise ResponseError(f"{where} must be an object")
    if extra := set(obj) - allowed:
        raise ResponseError(f"{where}: unexpected fields {sorted(extra)} (offsets, ids and dates are never accepted)")
    if missing := required - set(obj):
        raise ResponseError(f"{where}: missing fields {sorted(missing)} (every field must be stated; no defaults)")


def _enum(value, allowed, where):
    if value not in allowed:
        raise ResponseError(f"{where}: {value!r} is not one of {', '.join(allowed)}")


def _text(value, where):
    if not isinstance(value, str) or not value.strip():
        raise ResponseError(f"{where} must be non-empty text")


def _label(value, where):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", value):
        raise ResponseError(f"{where} must be a lowercase label")


# --- conversion: one assertion -----------------------------------------------------------------------

class _Stop(Exception):
    def __init__(self, kind, detail):
        super().__init__(detail)
        self.kind, self.detail = kind, detail


def _find(text, needle, lo, hi, what, occurrence=None):
    """The exact (start, end) of `needle` within text[lo:hi]; never a guess."""
    starts, i = [], text.find(needle, lo, hi)
    while i != -1 and i + len(needle) <= hi:
        starts.append(i)
        i = text.find(needle, i + 1, hi)
    if not starts:
        raise _Stop("grounding-failure", f"{what} {needle!r} does not occur exactly in the {'evidence' if lo else 'message'}")
    if occurrence is not None:
        if occurrence > len(starts):
            raise _Stop("ambiguous-span", f"{what} {needle!r} occurs {len(starts)} times; occurrence {occurrence} does not exist")
        return starts[occurrence - 1], starts[occurrence - 1] + len(needle)
    if len(starts) > 1:
        raise _Stop("ambiguous-span", f"{what} {needle!r} occurs {len(starts)} times and nothing says which")
    return starts[0], starts[0] + len(needle)


def _candidate(a, n, obs, earlier, report, fmt):
    text = obs.content
    s, e = _find(text, a["evidence"], 0, len(text), "evidence", a.get("evidence_occurrence"))
    passage = Passage(obs.id, s, e, text[s:e])

    if a["basis"] == "inferred":
        raise _Stop("inferred-not-admissible", "the model says it inferred this; formation:v1 would form it without "
                                               "review, so it is not admitted")

    participants = []
    for p in a["participants"]:
        surface = p["text"]
        if p["is_pronoun_or_vague"] or surface in PRONOUNS or surface.lower() in LOWER_PRONOUNS - {"i"}:
            raise _Stop("ambiguous-reference", f"{surface!r} is a pronoun or vague reference: identity is never inferred")
        if surface == "I" and not obs.author_id:
            raise _Stop("ambiguous-reference", "'I' with no known author")
        ps, pe = _find(text, surface, s, e, "participant")
        participants.append(Participant(p["role"], surface, ps, pe, p["kind"]))

    values = []
    if a.get("title"):
        if a["relation"] != "employment":
            raise _Stop("grounding-failure", "a title belongs to an employment")
        _find(text, a["title"], s, e, "title")
        values.append(("job-title", a["title"]))
    if a["relation"] == "statement":
        if not a.get("predicate"):
            raise _Stop("grounding-failure", "a statement needs a predicate")
        values.append(("predicate-text", a["predicate"].strip()))
        if a["predicate"].strip().lower() not in passage.text.lower():
            report.flags.append({"kind": "predicate-paraphrased", "assertion": n, "detail": a["predicate"]})
        if a.get("object_text"):
            _find(text, a["object_text"], s, e, "object text")
            values.append(("object-text", a["object_text"]))

    times = []
    for t in a["times"]:
        ts, te = _find(text, t["text"], s, e, "time")
        reading = timeexpr.read(t["text"], obs.observed_at, timeexpr.direction(text, ts))
        if reading is None and t["kind"] == "holds-at" and PRESENT.fullmatch(t["text"].strip()):
            # the rules:v2 reading of a present-tense verb: it holds at the moment the message was written
            times.append(TimeEvidence("holds-at", t["text"], ts, te, obs.observed_at, obs.observed_at, "instant", True,
                                      "present tense: at the observation time"))
            continue
        if reading is None:
            times.append(TimeEvidence(t["kind"], t["text"], ts, te, None, None, "unknown", True, "could not be read"))
            report.flags.append({"kind": "unreadable-time", "assertion": n, "detail": t["text"]})
        else:
            times.append(TimeEvidence(t["kind"], t["text"], ts, te, reading.earliest, reading.latest, reading.precision,
                                      reading.explicit, reading.assumption))

    # polarity, modality and certainty: the evidence, read from the start of its sentence (a model must not
    # escape a leading "I think" or "If" by quoting only what follows), must not contradict the model's reading
    lead = max(text.rfind(ch, 0, s) for ch in ".!?\n") + 1
    asserted = CONTRAST.sub("", text[lead:e])   # "joined in April, not March" asserts, it does not deny
    if a["polarity"] == "positive" and NEGATION.search(asserted):
        raise _Stop("cue-conflict", f"the evidence has a negation ({NEGATION.search(asserted).group()!r}) "
                                    "but the polarity is positive")
    if a["modality"] == "actual" and FUTURE_OR_CONDITIONAL.search(asserted):
        raise _Stop("cue-conflict", f"the evidence is future or conditional ({FUTURE_OR_CONDITIONAL.search(asserted).group()!r}) "
                                    "but the modality is actual")
    commitment = a["commitment"]
    if commitment == "certain" and (HEDGE.search(asserted) or a.get("allegation")):
        cue = HEDGE.search(asserted).group() if HEDGE.search(asserted) else "an allegation"
        commitment = "unknown"   # never kept as certain against a hedge: formation sends "unknown" to review
        report.flags.append({"kind": "commitment-downgraded", "assertion": n, "detail": f"certain → unknown ({cue!r})"})
    if a.get("allegation"):
        report.flags.append({"kind": "allegation", "assertion": n, "detail": "no contract field for an allegation (C4)"})

    attribution = _attribution(a["attribution"], obs, s, e, n, report, fmt)
    relations = _correction(a, n, obs, participants, times, earlier, report)
    return Candidate(a["relation"], passage, tuple(participants), tuple(sorted(values)), tuple(times), a["polarity"],
                     a["modality"], commitment, attribution, relations, "explicit", None)


def _attribution(at, obs, s, e, n, report, fmt):
    text, mode, claimant = obs.content, at["mode"], at["claimant"]
    via = []
    for v in at["via"]:
        if v not in text:
            raise _Stop("grounding-failure", f"intermediary {v!r} is not in the message")
        via.append(v)
    sender = None
    for lo, hi, forwarded_by in rules_v2._regions(text):
        if forwarded_by is not None and lo <= s and e <= hi:
            sender = forwarded_by or None
            if mode != "forwarded":
                report.flags.append({"kind": "mode-forced-forwarded", "assertion": n, "detail": f"{mode} → forwarded"})
                mode = "forwarded"
            if sender and claimant and claimant != sender:
                raise _Stop("cue-conflict", f"the claimant {claimant!r} is not the forwarded message's sender {sender!r}")
            claimant = claimant or sender
            break
    else:
        if mode == "forwarded":
            report.flags.append({"kind": "forwarded-unmarked", "assertion": n, "detail": "no forward marker in the message"})
    if claimant is not None:
        if claimant in PRONOUNS or claimant.lower() in LOWER_PRONOUNS:
            raise _Stop("ambiguous-reference", f"the claimant {claimant!r} is a pronoun")
        if claimant not in text:
            raise _Stop("grounding-failure", f"claimant {claimant!r} is not in the message")
        # C2: the kind the model states, in the 1.1 vocabulary; a forward header's sender is of unknown kind
        kind = CLAIMANT_KINDS[fmt][at["claimant_kind"]] if at["claimant"] is not None else "unknown"
    else:
        kind = None
    # via, nearest first: the message's author (as rules:v2 records it), then intermediaries the text names
    nearest = (obs.author_id,) if obs.author_id and mode != "direct" else ()
    return Attribution(claimant, mode, nearest + tuple(v for v in via if v not in nearest),
                       ("forwarded",) if mode == "forwarded" else (), kind)


def _correction(a, n, obs, participants, times, earlier, report):
    corr = a.get("correction")
    if corr is None:
        return ()
    if corr["cue"] not in obs.content:
        raise _Stop("grounding-failure", f"correction cue {corr['cue']!r} is not in the message")
    roles = sorted((p.role, p.surface.casefold()) for p in participants)
    kinds = {t.kind for t in times} & {"start", "end", "holds-since"}
    matches = [c for c in earlier if c.claim_type == a["relation"]
               and sorted((p.role, p.surface.casefold()) for p in c.participants) == roles
               and (not kinds or kinds & {t.kind for t in c.times})]
    if len(matches) == 1:
        return (Relation(corr["kind"], matches[0].id, "stated", corr["cue"]),)
    if corr["kind"] not in NULLABLE_TARGET_KINDS:
        raise _Stop("correction-target-unresolved",
                    f"{len(matches)} earlier candidates could be the target of a {corr['kind']!r}, which must name one")
    # D3 (format 1.1): never a guessed target; a null target, which formation always sends to review
    report.flags.append({"kind": "correction-target-unresolved", "assertion": n,
                         "detail": f"{len(matches)} earlier candidates could be the target: left unestablished"})
    return (Relation(corr["kind"], None, "stated", corr["cue"]),)


# --- R2: bare retractions ------------------------------------------------------------------------------

def _sentence(text, at):
    lo = max(text.rfind(ch, 0, at) for ch in ".!?\n") + 1
    m = SENTENCE_END.search(text, at)
    hi = m.start() if m else len(text)
    while lo < hi and text[lo].isspace():
        lo += 1
    while hi > lo and text[hi - 1].isspace():
        hi -= 1
    return lo, hi


def _bare_retractions(obs, made, earlier, report):
    """A candidate for each retraction in the message that no assertion already carries.

    The candidate is what the author asserts, a retraction: a generic statement with the author ("I") as subject,
    the retraction phrase as predicate, what it is about as object text, and a `retracts` relation with a null
    target. Its target is never chosen: formation sends a null-target retraction to review, and nothing is
    superseded. Earlier candidates in the thread that mention what it is about are listed for the reviewer in a
    flag, never applied."""
    text, out = obs.content, []
    cued = [(c.passage.start, c.passage.end) for c in made for r in c.relations if r.kind in ("retracts", "corrects")]
    for m in BARE_RETRACTION.finditer(text):
        if NOT_BEFORE.search(text[max(0, m.start() - 16):m.start()]):
            continue  # "don't forget what I said" is not a retraction
        s, e = _sentence(text, m.start())
        if any(lo < e and s < hi for lo, hi in cued):
            continue  # an assertion already carries this retraction
        i_at = [x.start() for x in re.finditer(r"\bI\b", text[s:e])]
        if not obs.author_id or not i_at:
            report.outcomes.append({"kind": "bare-retraction-unrecorded", "assertion": None, "evidence": text[s:e],
                                    "detail": "a retraction with no author or no first person to attach it to: "
                                              "reported here, not stored"})
            continue
        rest = text[m.end():e]
        about = re.split(r"[,;:]", rest, maxsplit=1)[0].strip()
        values = [("predicate-text", m.group())]
        if about:
            values.append(("object-text", about))
        names = set(re.findall(r"\b[A-Z][\w'-]+", about))
        possible = sorted({c.id for c in earlier
                           if names & {w for p in c.participants for w in p.surface.split()}})
        c = Candidate("statement", Passage(obs.id, s, e, text[s:e]),
                      (Participant("subject", "I", s + i_at[0], s + i_at[0] + 1, "person"),), tuple(sorted(values)),
                      (), "positive", "actual", "certain", Attribution(),
                      (Relation("retracts", None, "stated", m.group()),), "explicit", None)
        n = len(made) + len(out)
        report.flags.append({"kind": "bare-retraction", "assertion": n,
                             "detail": f"{m.group()!r}: a retraction that does not restate its target; sent to review"})
        report.flags.append({"kind": "retraction-possible-targets", "assertion": n,
                             "detail": ", ".join(possible) if possible else "none found in the thread"})
        out.append(c)
        cued.append((s, e))  # one candidate per sentence, however many cues it has
    return out
