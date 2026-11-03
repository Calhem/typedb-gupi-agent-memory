"""`rules:v2`: an offline, deterministic candidate extractor for a deliberately narrow domain
(docs/formation/rules-v2.md).

It reads employment ("joined", "left", "works at", "has worked at ... since") and reporting lines ("reports
to", "stopped reporting to", "has reported to ... since") one sentence at a time. It emits
`gupi.candidate/1` sets that keep the exact passage, the time phrases with their kinds, polarity, modality,
the source's commitment, attribution, and correction or repeat relations (audit.md A1-A5, A7).

It writes nothing anywhere: candidates stay separate from memory. Its `confidence` is always None, because
a rule extractor has no calibrated confidence. That is the extractor's view, kept apart from the source's
commitment and from any later acceptance. `rules:v1` (gupi.extraction.rules) stays the default and is
unchanged.
"""

import re
from dataclasses import dataclass, field, replace

from gupi import ids, timeexpr
from gupi.formation.candidate import (
    Attribution, Candidate, CandidateSet, Participant, Passage, Relation, TimeEvidence,
)
from gupi.formation.validate import validate

NAME = r"[A-Z][a-z]+(?: [A-Z][a-z]+)?"
TIME = (r"(?:\d{1,2} [A-Z][a-z]+ \d{4}|[A-Z][a-z]+ \d{1,2},? \d{4}|[A-Z][a-z]+ \d{4}|\d{4}"
        r"|(?:January|February|March|April|May|June|July|August|September|October|November|December)"
        r"|(?:last|next) (?:spring|summer|autumn|fall|winter|week|month|year)|later this year|this year"
        r"|yesterday|today)")
T = rf"(?:the end of |early |late )?(?P<t>{TIME})"
WHEN = rf"(?:(?: (?:in|on|at))? {T})?"
TITLE = r"(?: as (?:an? |the )?(?P<title>[A-Za-z][A-Za-z ]*?))?"
HEDGE = r"(?:(?P<hedge>probably|possibly|perhaps|apparently) )?"
STILL = r"(?:(?:still|now|currently) )?"
TAIL = r"(?:,? not [^.]*| now| any ?more| these days)?"
WHO = rf"(?P<who>{NAME}|I)"

# (claim type, pattern, {group: role}, what it says, modality). Roles: employee/employer, report/manager.
EMP = {"who": "employee", "org": "employer"}
REP = {"who": "report", "boss": "manager"}
ORG = rf"(?P<org>{NAME})"
BOSS = rf"(?P<boss>{NAME})"
PATTERNS = [
    ("employment", rf"{WHO}, who joined {ORG}{WHEN},.*", EMP, "start", "actual"),
    ("employment", rf"{WHO} was promoted to (?P<title>[A-Za-z ]+?) at {ORG}{WHEN}", EMP, "start", "actual"),
    ("employment", rf"{WHO} (?:joined|started at|was hired by) {ORG}{TITLE}{WHEN}{TITLE.replace('title', 'title2')}{TAIL}",
     EMP, "start", "actual"),
    ("employment", rf"{WHO} left {ORG}{WHEN}{TAIL}", EMP, "end", "actual"),
    ("employment", rf"{WHO} (?:is leaving|will leave|plans to leave|is due to leave) {ORG}{WHEN}", EMP, "end", "planned"),
    ("employment", rf"{WHO} (?:(?P<modal>will|might|may|could|plans to|is going to|is expected to) join|is joining)"
                   rf" {ORG}{WHEN}", EMP, "start", "planned"),
    ("employment", rf"{WHO} has (?:worked|been) (?:at|for|with) {ORG} since {T}", EMP, "since", "actual"),
    ("employment", rf"{WHO} (?:no longer works|does not work|doesn't work) (?:at|for) {ORG}{TAIL}", EMP, "not", "actual"),
    ("employment", rf"{WHO} (?:is not|isn't) (?:with|at) {ORG}{TAIL}", EMP, "not", "actual"),
    ("employment", rf"{WHO} {HEDGE}{STILL}(?P<now>works|is working) (?:at|for) {ORG}{TITLE}{TAIL}", EMP, "now", "actual"),
    ("reporting", rf"{WHO} stopped reporting to {BOSS}{WHEN}", REP, "end", "actual"),
    ("reporting", rf"{WHO} has (?:reported|been reporting) to {BOSS} since {T}", REP, "since", "actual"),
    ("reporting", rf"{WHO} (?:no longer reports|does not report|doesn't report) to {BOSS}{TAIL}", REP, "not", "actual"),
    ("reporting", rf"{WHO} {HEDGE}{STILL}(?P<now>reports|is reporting|has been reporting) to {BOSS}{TAIL}", REP, "now",
     "actual"),
]
KINDS = {"employee": "person", "employer": "organization", "report": "person", "manager": "person"}
DOMAIN_VERB = re.compile(r"\b(?:joined|left|works?|worked|working|reports?|reporting|reported|hired|promoted|rejoined|manages?)\b")

# Leading cues, removed in order before the patterns are tried; each is recorded on the candidate.
CORRECTION = re.compile(r"Correction(?: to [^:]+)?:\s*")
REPORTED = re.compile(rf"(?:(?P<a>{NAME}) (?:told me|says|said|mentioned|wrote)(?: that)? |According to (?P<b>{NAME}), )")
RUMOUR = re.compile(r"(?:Reportedly|I hear(?:d)?(?: that)?|Word is(?: that)?),? ")
PREFIX_HEDGE = re.compile(r"(?P<h>I think|I believe|Probably|Possibly|Maybe|Perhaps|Apparently),? ")
LEADING_TIME = re.compile(rf"(?P<kw>Since|From) {T},? |As of (?:today|now),? ")
FORWARD = re.compile(r"^-{2,} ?Forwarded message ?-{2,}$|^Begin forwarded message:$", re.M)
HEADER = re.compile(r"^(?:From|To|Date|Subject|Sent|Cc): ?(?P<v>.*)$")
SENTENCE = re.compile(r"[^.!?\n]+[.!?]?")
CLAUSE = re.compile(rf",? and (?=(?:{NAME} )?(?:reports|works|joined|left|has|is) )")
HEDGES = {"I think": "probable", "I believe": "probable", "Probably": "probable", "probably": "probable",
          "Apparently": "probable", "apparently": "probable", "Possibly": "possible", "possibly": "possible",
          "Maybe": "possible", "Perhaps": "possible", "perhaps": "possible"}
MODALS = {"might": "possible", "may": "possible", "could": "possible", "is expected to": "probable"}


@dataclass
class Report:
    """What the extractor did not turn into candidates, and why. Not part of the candidate representation."""

    rejected: list = field(default_factory=list)   # (sentence, reason)
    notes: list = field(default_factory=list)


class RulesV2:
    method = "rules:v2"

    def extract(self, observation, prior=(), schema=None):
        """(CandidateSet, Report) for one observation. `prior`: earlier sets in the same thread, used only to
        name the target of a stated correction. Deterministic: the same input gives the same ids."""
        text, report = observation.content, Report()
        candidates = []
        for region_start, region_end, forwarded_by in _regions(text):
            for s in SENTENCE.finditer(text, region_start, region_end):
                start = s.start() + len(s.group()) - len(s.group().lstrip())
                end = s.end()
                if start >= end or HEADER.match(text[start:end].strip()):
                    continue
                found = self._sentence(text, start, end, observation, forwarded_by, report)
                for c in found:
                    candidates.append(self._relate(c, candidates, prior, report))
        cset = CandidateSet(observation.id, ids.content_hash(text), self.method, ())
        kept = []
        for c in candidates:
            issues = validate(replace(cset, candidates=(c,)), observation, schema)
            relation_only = [i for i in issues if i.code != "relation"]
            if relation_only:
                report.rejected.append((c.passage.text, "; ".join(i.message for i in relation_only)))
            else:
                kept.append(c)
        return replace(cset, candidates=tuple(dict.fromkeys(kept))), report

    # --- one sentence ---------------------------------------------------------------------------------

    def _sentence(self, text, start, end, obs, forwarded_by, report):
        sentence = text[start:end]
        pos, cues = start, {"commitment": "certain", "mode": "forwarded" if forwarded_by is not None else "direct",
                            "asserted_by": forwarded_by or None, "correction": None, "leading": None}
        for rx, kind in ((CORRECTION, "correction"), (REPORTED, "reported"), (RUMOUR, "rumour"),
                         (PREFIX_HEDGE, "hedge"), (LEADING_TIME, "time")):
            m = rx.match(text, pos, end)
            if not m:
                continue
            if kind == "correction":
                cues["correction"] = m.group().strip()
            elif kind == "reported":
                cues["mode"], cues["asserted_by"] = "reported", m.group("a") or m.group("b")
            elif kind == "rumour":
                cues["mode"], cues["commitment"] = "rumour", "unknown"
            elif kind == "hedge":
                cues["commitment"] = HEDGES[m.group("h")]
            else:
                cues["leading"] = m
            pos = m.end()
        body_end = end - (1 if sentence.endswith((".", "!", "?")) else 0)
        clauses = [(pos, body_end)]
        if m := CLAUSE.search(text, pos, body_end):
            clauses = [(pos, m.start()), (m.end(), body_end)]
        found, subject = [], None
        for c_start, c_end in clauses:
            c = self._clause(text, c_start, c_end, start, end, obs, cues, subject)
            if c is None:
                if DOMAIN_VERB.search(text[c_start:c_end]):
                    report.rejected.append((text[c_start:c_end], "a domain verb, but no supported pattern "
                                                                 "(missing role player, pronoun or unsupported phrasing)"))
                continue
            candidate, subject = c
            found.append(candidate)
        for f in found:
            for t in f.times:
                if t.earliest is None:
                    report.notes.append(f"time phrase {t.phrase!r} could not be read; kept without a window")
        return found

    def _clause(self, text, c_start, c_end, s_start, s_end, obs, cues, subject):
        """One clause. A clause without its own subject ("... and reports to X") reuses the previous one's."""
        for claim_type, pattern, roles, says, modality in PATTERNS:
            m, who = re.compile(pattern).fullmatch(text, c_start, c_end), None
            if m is not None:
                who = (m.start("who"), m.end("who"), m.group("who"))
            elif subject is not None and pattern.startswith(WHO + " "):
                m = re.compile(pattern[len(WHO) + 1:]).fullmatch(text, c_start, c_end)
                who = subject if m else None
            if m is None:
                continue
            if who[2] == "I" and not obs.author_id:
                return None  # first person with no known author: nobody to attribute it to
            participants = [Participant(roles["who"], who[2], who[0], who[1], KINDS[roles["who"]])]
            for group, role in roles.items():
                if group != "who":
                    participants.append(Participant(role, m.group(group), m.start(group), m.end(group), KINDS[role]))
            values = tuple(sorted(("job-title", v.strip()) for g in ("title", "title2")
                                  if g in m.re.groupindex and (v := m.group(g))))
            commitment = cues["commitment"]
            if "hedge" in m.re.groupindex and m.group("hedge"):
                commitment = HEDGES[m.group("hedge")]
            if "modal" in m.re.groupindex and m.group("modal") in MODALS:
                commitment = MODALS[m.group("modal")]
            attribution = Attribution(cues["asserted_by"], cues["mode"],
                                      (obs.author_id,) if obs.author_id and cues["mode"] != "direct" else (),
                                      ("forwarded",) if cues["mode"] == "forwarded" else ())
            relations = (Relation("corrects", "?", "stated", cues["correction"]),) if cues["correction"] else ()
            candidate = Candidate(
                claim_type, Passage(obs.id, s_start, s_end, text[s_start:s_end]), tuple(participants), values,
                _times(text, obs, m, says, cues["leading"]), "negative" if says == "not" else "positive", modality,
                commitment, attribution, relations)
            return candidate, who
        return None

    # --- relations ----------------------------------------------------------------------------------

    def _relate(self, c, earlier, prior, report):
        """Name the target of a stated correction, and mark a forwarded copy of an earlier statement."""
        relations = []
        for r in c.relations:
            if r.kind != "corrects":
                relations.append(r)
                continue
            target = _same_boundary(c, [x for s in prior for x in s.candidates] + list(earlier))
            if target is None:
                report.notes.append(f"correction cue {r.cue!r} in {c.passage.text!r}: no earlier candidate about the "
                                    "same proposition and boundary, so no relation was recorded")
            else:
                relations.append(Relation("corrects", target.id, "stated", r.cue))
        if c.attribution.mode == "forwarded":
            original = next((x for x in earlier if x.attribution.mode != "forwarded" and _same_statement(x, c)), None)
            if original is not None:
                relations.append(Relation("repeats", original.id, "inferred"))
        return replace(c, relations=tuple(relations))


def _regions(text):
    """(start, end, forwarded-by) regions: the text before a forward marker, then each forwarded part.
    forwarded-by is "" for a forwarded part without a From: header, None for the author's own text."""
    marks = list(FORWARD.finditer(text))
    if not marks:
        return [(0, len(text), None)]
    regions = [(0, marks[0].start(), None)]
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        sender = ""
        for line in text[m.end():end].splitlines():
            if h := HEADER.match(line.strip()):
                if line.strip().startswith("From:"):
                    sender = h.group("v").strip()
        regions.append((m.end(), end, sender))
    return regions


def _times(text, obs, m, says, leading):
    out = []
    kind = {"start": "start", "end": "end", "since": "holds-since"}.get(says)
    if kind and "t" in m.re.groupindex and m.group("t"):
        out.append(_evidence(text, obs, kind, m.start("t"), m.end("t")))
    if leading is not None and leading.group("t"):  # "Since March, ..." / "From March, ..."
        k = "holds-since" if leading.group("kw") == "Since" else "start"
        if not any(t.kind == k for t in out):
            out.append(_evidence(text, obs, k, leading.start("t"), leading.end("t")))
    if says in ("now", "since", "not"):  # present tense: it holds (or does not) at the observation time
        a, b = m.span("now") if "now" in m.re.groupindex and m.group("now") else _verb_span(text, m)
        out.append(TimeEvidence("holds-at", text[a:b], a, b, obs.observed_at, obs.observed_at, "instant", True,
                                "present tense: at the observation time"))
    return tuple(out)


VERB = re.compile(r"has (?:worked|been reporting|been|reported)|no longer \w+|does not \w+|doesn't \w+|is not|isn't")


def _verb_span(text, m):
    """The verb phrase after the subject ("has worked", "no longer works"), as the present-tense phrase."""
    after = m.end("who") if "who" in m.re.groupindex and m.group("who") else m.start()
    v = VERB.search(text, after, m.end())
    return v.span() if v else (after, after)


def _evidence(text, obs, kind, start, end):
    phrase = text[start:end]
    reading = timeexpr.read(phrase, obs.observed_at, timeexpr.direction(text, start))
    if reading is None:
        return TimeEvidence(kind, phrase, start, end, None, None, "unknown", True, "could not be read")
    return TimeEvidence(kind, phrase, start, end, reading.earliest, reading.latest, reading.precision,
                        reading.explicit, reading.assumption)


def _roles(c):
    return c.claim_type, tuple(sorted((p.role, p.surface.casefold()) for p in c.participants))


def _same_boundary(c, others):
    kinds = {t.kind for t in c.times} & {"start", "end", "holds-since"}
    for x in reversed(others):
        if _roles(x) == _roles(c) and x.polarity == c.polarity and kinds & {t.kind for t in x.times} and x is not c:
            return x
    return None


def _same_statement(a, b):
    return (_roles(a) == _roles(b) and a.polarity == b.polarity
            and sorted((t.kind, t.earliest, t.latest) for t in a.times) == sorted((t.kind, t.earliest, t.latest) for t in b.times))
