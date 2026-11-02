"""The offline default extractor: deterministic patterns for the `people` domain, no API calls.

Deliberately simple and transparent. It reads one sentence at a time, recognises a small set of phrasings
(reporting lines, joining/leaving/working at an organisation, a few generic statements) and returns the
extraction contract (gupi.extraction.contract), so its output goes through the same validator as any
LLM's. It does not resolve pronouns, handle negation or read more than one clause per sentence; those
misses are measured in the evaluation, not hidden.
"""

import hashlib
import re

NAME = r"[A-Z][a-z]+(?: [A-Z][a-z]+)?"
TITLE = r"[A-Z][A-Za-z]*(?: (?:of|and|[A-Z][A-Za-z]*))*"
TIME = r"(?:\d{1,2} [A-Z][a-z]+ \d{4}|[A-Z][a-z]+ \d{1,2},? \d{4}|[A-Z][a-z]+ \d{4}|\d{4}(?:-\d{2}){0,2}|[A-Z][a-z]+|last (?:week|month|year)|yesterday|today)"
ARTICLE = r"(?:(?:a|an|the) )?"

# (claim type, regex, how groups map to roles, values, time and tense)
PATTERNS = [
    ("reporting", rf"(?P<report>{NAME}) stopped reporting to (?P<manager>{NAME})(?: (?:in|on) (?P<end>{TIME}))?", "ended"),
    ("reporting", rf"(?P<report>{NAME}) has reported to (?P<manager>{NAME})(?: since (?P<start>{TIME}))?", "ongoing"),
    ("reporting", rf"(?P<report>{NAME}) (?:now |still )?reports to (?P<manager>{NAME})", "ongoing"),
    ("employment", rf"(?P<employee>{NAME}) joined (?P<employer>{NAME})(?: as {ARTICLE}(?P<title>{TITLE}))?"
                   rf"(?: (?:in|on) (?P<start>{TIME}))?", "past"),
    ("employment", rf"(?P<employee>{NAME}) left (?P<employer>{NAME})(?: (?:in|on) (?P<end>{TIME}))?", "ended"),
    ("employment", rf"(?P<employee>{NAME}) works (?:at|for) (?P<employer>{NAME})(?: as {ARTICLE}(?P<title>{TITLE}))?", "ongoing"),
    ("employment", rf"(?P<employee>{NAME}) is {ARTICLE}(?P<title>{TITLE}) at (?P<employer>{NAME})", "ongoing"),
    ("statement", rf"(?P<subject>{NAME}) (?P<predicate>is learning|lives in|likes) (?P<object>[A-Za-z][\w ]*?)$", "ongoing"),
]
ROLE_KINDS = {"report": "person", "manager": "person", "employee": "person", "employer": "organization",
              "subject": "person"}
LEADING_TIME = re.compile(rf"^(?:Since|From) (?P<start>{TIME}),? ")
PREFIX = re.compile(r"^(?:[A-Z][a-z]+(?: [a-z]+)?: )")  # "Correction: ", "Quick intro: "
SENTENCE = re.compile(r"[^.!?]+[.!?]?")


class RuleExtractor:
    method = "rules:v1"
    model = None
    prompt_version = "rules-v1"
    prompt_hash = hashlib.sha256(repr(PATTERNS).encode()).hexdigest()[:16]

    def extract(self, request):
        text = request.text
        mentions, claims = [], []
        for s in SENTENCE.finditer(text):
            sentence, offset = s.group().strip(), s.start() + (len(s.group()) - len(s.group().lstrip()))
            body = sentence.rstrip(".!?")
            if p := PREFIX.match(body):
                body, offset = body[p.end():], offset + p.end()
            start_phrase = None
            if lt := LEADING_TIME.match(body):
                start_phrase, body, offset = lt.group("start"), body[lt.end():], offset + lt.end()
            for claim_type, pattern, tense in PATTERNS:
                m = re.fullmatch(pattern, body)
                if m:
                    claims.append(self._claim(claim_type, m, tense, offset, sentence, text, mentions, start_phrase))
                    break
        return {"mentions": mentions, "claims": claims}

    @staticmethod
    def _claim(claim_type, m, tense, offset, sentence, text, mentions, start_phrase):
        roles = {}
        for role, kind in ROLE_KINDS.items():
            if role in m.groupdict() and m.group(role):
                mid = f"m{len(mentions) + 1}"
                mentions.append({"id": mid, "text": m.group(role), "start": offset + m.start(role),
                                 "end": offset + m.end(role), "kind": kind})
                roles[role] = [mid]
        groups = m.groupdict()
        claim = {"type": claim_type, "roles": roles, "values": {}, "quote": sentence,
                 "start": text.index(sentence), "end": text.index(sentence) + len(sentence), "basis": "explicit",
                 "time": {"start": groups.get("start") or start_phrase, "end": groups.get("end"),
                          "ongoing": tense == "ongoing"}}
        if groups.get("title"):
            claim["values"]["job-title"] = groups["title"]
        if claim_type == "statement":
            claim["predicate"] = groups["predicate"]
            claim["object_text"] = groups["object"].strip()
        return claim
