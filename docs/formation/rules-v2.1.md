# `rules:v2.1`: rules:v2 with the D1 and D2 corrections

**What changes, and what does not:**
- **Changed:** two corrections from the Phase 7A diagnosis (docs/evaluation/phase-7a/pipeline-audit.md).
- **Unchanged:**
  - **Behaviour kept:** the patterns, the candidate representation (`gupi.candidate/1`), validation,
    formation, proposition keys, the schema and migrations.
  - **`rules:v2` itself:** it stays selectable, so every earlier result can be reproduced.

## Choosing a version
```python
from gupi.formation import extractors

extractors.get("rules:v2.1").extract(observation)   # with the corrections
extractors.get("rules:v2").extract(observation)     # exactly as in Phases 6B-7A
```
- **What is registered:** `extractors.VERSIONS` lists the registered versions. An unknown version raises
  `KeyError`.
- **Recording the version:** the version's `method` (`"rules:v2.1"` or `"rules:v2"`) is recorded on every
  candidate set and formed claim.
- **No caller was switched:**
  - **The evaluation runners:** those for Phases 6B, 6C, 6D and 7A still construct `RulesV2` directly, so
    rerunning them reproduces their committed results.
  - **New work:** it should name `rules:v2.1`.
  - **Making it the default anywhere:** that is a decision for review.

## D1: pronouns are not names (correctness)
**The defect:** `rules:v2` matched names with `[A-Z][a-z]+`, so "She joined Halden in March 2025."
became employment(employee "She"). formation:v1 formed it, and it was believed. Every "She" in a
conversation then shared one invented person.

**What `rules:v2.1` does instead:**
- **Pronouns are rejected, never resolved:** it rejects a clause whose candidate would have a capitalised
  pronoun as a participant, or as the reported speaker ("She told me that ..."). The list includes She, He,
  They, We, You, It, Him, Her, Them, Us, Me, the possessives, This, That, Someone and Everyone.
- **The rejection is explicit:** "an unresolved reference: 'She' is a pronoun, not a name (no coreference is
  attempted)".
- **No coreference:** an earlier name in the same message or thread is not used.
- **"I":** is still the observation's author, as the contract defines. With no known author, it is reported
  as "first person with no known author".
- **Real names still work:** names that begin like a pronoun ("Shea Brandt", "Theo"), and two-word names
  whose first word is one ("He Wei"), still extract.
- **Nothing to resolve, nothing reported:** a pronoun speaker with no domain content ("She told me she loves
  painting.") produces no "unresolved reference", because there is no candidate whose reference is
  missing.

## D2: unsupported expressions are reported (diagnostic coverage)
**The defect:** `rules:v2` reported unparsed sentences only when they contained one of its domain verbs. So
"began working for", "took a job at", "quit", "resigned from", "was appointed", "is employed by", "was let
go" and "boss" disappeared silently.

**What `rules:v2.1` does instead:**
- **The report:** it names such sentences as "an employment or reporting expression rules:v2.1 does not
  support ('<the expression>')". This also covers the Phase 7A sample's "lost my job", "got a temp job" and
  "accepted for an internship".
- **Employment context required:** each expression needs it. "It began to rain", "quit smoking", "the
  appointed time", "took the bus", "let go of the rope" and "the boss fight" are not reported.
- **No new patterns:** these expressions produce no candidates. Reporting never changes the candidates or
  the formation decisions.

## Kinds of outcome (`rules_v21.reason_kind`)
| Kind | Meaning |
|---|---|
| `unresolved-reference` | a pronoun where a name is needed |
| `no-author` | "I" with no known author |
| `unsupported-expression` | an employment or reporting expression with no pattern |
| `no-pattern` | `rules:v2`'s generic reason: a domain verb, but no supported pattern |
| `validation` | the candidate failed validation (the validator's own message) |

An empty or whitespace-only input yields no candidates and no rejections.

## Remaining limits
- **No coreference:**
  - **What is lost:** information carried by pronouns is now rejected rather than wrongly admitted.
  - **The trade:** this is deliberate, and it costs recall wherever a pronoun refers back to a named person.
- **Lowercase pronouns** ("she", "they") never matched a name and are still silent unless a domain verb is
  present.
- **D2's expression list is fixed and diagnostic:**
  - **Some reports cover non-employment roles:** institutional appointments ("judges are appointed") and
    "your boss" in advice text are reported too.
  - **Some expressions are not listed at all.**
- **Everything else in rules-v2.md still applies:** the narrow domain, unnamed employers, and the leading and
  trailing words that defeat whole-clause matching.
