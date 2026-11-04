"""`rules:v2.1`: `rules:v2` with two corrections (docs/formation/rules-v2.1.md). Same patterns, same candidate
representation, same validation; `rules:v2` itself is unchanged and stays selectable.

- **D1 (correctness):** a capitalised pronoun ("She", "He", "They", "We", "It", "Him", ...) is never taken as a
  person's or organisation's name, nor as the asserter of reported speech. Such a clause yields no candidate
  and an explicit "unresolved reference" rejection. No coreference is attempted: an earlier name in the same
  message or thread is not used to resolve a later pronoun. "I" is still the observation's author, as
  before; with no known author it is now reported as such instead of under a generic reason.
- **D2 (diagnostic coverage):** a sentence with an employment or reporting expression the patterns do not
  support ("began working for", "took a job at", "quit", "resigned from", "was appointed", "is employed by",
  "was let go", "boss", and the Phase 7A sample's "lost my job", "got a temp job", "accepted for an internship")
  is reported as an unsupported expression. Nothing new is extracted, and reporting never
  changes which candidates exist or how they are formed. Unrelated uses ("It began to rain", "quit smoking",
  "the appointed time") are not reported.

Every rejection reason has one of five kinds (`reason_kind`): unresolved-reference, no-author,
unsupported-expression, no-pattern (rules:v2's generic reason) and validation (the validator's message).
"""

import re

from gupi.formation import rules_v2 as v2

UNRESOLVED = "an unresolved reference"
NO_AUTHOR = "first person with no known author"
UNSUPPORTED = "an employment or reporting expression rules:v2.1 does not support"

PRONOUNS = frozenset({
    "He", "She", "They", "We", "You", "It", "Him", "Her", "Them", "Us", "Me", "His", "Hers", "Their", "Theirs",
    "Our", "Ours", "Its", "My", "Mine", "Your", "Yours", "This", "That", "These", "Those", "Someone", "Somebody",
    "Everyone", "Everybody", "Nobody", "Anyone", "Anybody",
})

# Employment or reporting expressions with no rules:v2 pattern. Each needs an employment context, so that
# ordinary uses of the same words ("It began to rain", "quit smoking", "the appointed time") stay silent.
JOB = r"(?:job|position|role|post|career)"
UNSUPPORTED_EXPRESSIONS = re.compile("|".join([
    r"\bbegan (?:working|to work|work)\b",
    rf"\btook (?:a|an|the|up a|up the|on a|on the)(?: \w+){{0,2}}? {JOB}\b",
    r"\btook over as\b",
    rf"\bquit (?:my|his|her|their|our|your|the|a|an) (?:\w+ )?{JOB}\b",
    r"\bquit (?!smoking\b|drinking\b)[A-Z][a-z]+\b",
    r"\bresign(?:ed|s|ing)? (?:from|as)\b",
    r"\b(?:was|were|been|being|is|are|got|get|gets) (?:\w+ )?appointed\b",
    r"\b(?:is|was|are|were|am|been|be) (?:\w+ )?employed (?:by|at|as|with)\b",
    r"\b(?:was|were|been|being|got|get|gets) let go\b",
    r"\b(?:was|were|been|got|get|gets) (?:laid off|fired)\b",
    r"(?:'s|\bmy|\bhis|\bher|\btheir|\bour|\byour|\bthe new) boss\b(?! fight| level| battle)",
    rf"\blost (?:my|his|her|their|our|your|a|the) (?:\w+ )?{JOB}\b",            # the Phase 7A sample's phrasings
    r"\bgot (?:a|an|the) (?:\w+ )?(?:job|position|role|internship|placement)\b",
    r"\b(?:accepted|hired|selected) (?:for|into) (?:a|an|the) (?:\w+ )?(?:job|position|role|internship|placement)\b",
]))


def reason_kind(reason):
    """The kind of a rejection reason: unresolved-reference | no-author | unsupported-expression | no-pattern |
    validation."""
    if reason.startswith(UNRESOLVED):
        return "unresolved-reference"
    if reason.startswith(NO_AUTHOR):
        return "no-author"
    if reason.startswith(UNSUPPORTED):
        return "unsupported-expression"
    if reason.startswith("a domain verb, but no supported pattern"):
        return "no-pattern"
    return "validation"


class RulesV21(v2.RulesV2):
    method = "rules:v2.1"

    def _sentence(self, text, start, end, obs, forwarded_by, report):
        self._why = {}
        before = len(report.rejected)
        found = super()._sentence(text, start, end, obs, forwarded_by, report)
        # D1: a specific reason replaces the generic one; rejections the base would not report are added
        new = [(clause, self._why.pop(clause, reason)) for clause, reason in report.rejected[before:]]
        new += list(self._why.items())
        # D2: an unsupported employment or reporting expression is named as such
        if not found and (m := UNSUPPORTED_EXPRESSIONS.search(text, start, end)):
            if not any(reason_kind(r) in ("unresolved-reference", "no-author") for _, r in new):
                cue = f"{UNSUPPORTED} ({m.group().strip()!r})"
                new = [(c, cue) for c, r in new if reason_kind(r) == "no-pattern"] or [(text[start:end].rstrip(".!?"), cue)]
        report.rejected[before:] = new
        return found

    def _clause(self, text, c_start, c_end, s_start, s_end, obs, cues, subject):
        clause = text[c_start:c_end]
        result = super()._clause(text, c_start, c_end, s_start, s_end, obs, cues, subject)
        if result is None:
            if not obs.author_id and re.match(r"I\b", clause.lstrip()) and v2.DOMAIN_VERB.search(clause):
                self._why[clause] = f"{NO_AUTHOR}: nobody to attribute 'I' to"
            return None
        candidate, _ = result
        bad = sorted({p.surface for p in candidate.participants if p.surface in PRONOUNS})
        if candidate.attribution.asserted_by in PRONOUNS:
            bad.append(f"{candidate.attribution.asserted_by} (the reported speaker)")
        if bad:  # only when a candidate would otherwise be formed: there is a reference to resolve
            self._why[clause] = (f"{UNRESOLVED}: {', '.join(repr(b) for b in bad)} is a pronoun, not a name "
                                 "(no coreference is attempted)")
            return None
        return result
