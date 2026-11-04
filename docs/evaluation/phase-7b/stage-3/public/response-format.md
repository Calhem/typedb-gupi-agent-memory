# Response format `gupi.model-response/1.1`

This is the exact format GUPI's parser (`model:candidate-v1.1`) accepts. It turns each response into GUPI
candidates in format `gupi.candidate/1.1`, which are then validated and passed to memory formation. **Any
field not listed here, and any missing field, makes the whole response invalid.** There are no defaults.

## Why the response is not the candidate itself
A `gupi.candidate/1.1` candidate holds character offsets, computed dates and resolved correction targets.
**You never supply those.** You quote text exactly. GUPI's code then:
- finds every quoted string in the passage, and computes the offsets
- reads every time phrase into a date range itself, using the document date
- detects forwarded text from the passage's own forward markers
- resolves correction targets against earlier passages in the same thread, or leaves them unresolved for a
  human reviewer

A response that supplies offsets, dates or ids is rejected.

## Top level
```json
{"format": "gupi.model-response/1.1", "outcome": "assertions", "assertions": [ ... ], "problems": [ ... ]}
```
| Field | Values |
|---|---|
| `format` | exactly `"gupi.model-response/1.1"` |
| `outcome` | `"assertions"`, or `"no-relevant-assertion"` (then `assertions` must be `[]`) |
| `assertions` | a list of assertion objects (below); may be empty |
| `problems` | a list of problem objects (below); may be empty |

## An assertion
| Field | Required | Values |
|---|---|---|
| `evidence` | yes | the exact text of the smallest span of the passage that states the assertion, copied character for character |
| `evidence_occurrence` | only if `evidence` occurs more than once in the passage | 1 for the first occurrence, 2 for the second, … |
| `relation` | yes | `employment`, `reporting` or `statement` (below) |
| `participants` | yes, at least one | a list of `{"role", "text", "kind", "is_pronoun_or_vague"}` |
| `times` | yes (may be `[]`) | a list of `{"text", "kind"}` |
| `polarity` | yes | `positive`, `negative` |
| `modality` | yes | `actual`, `planned`, `required`, `permitted`, `requested`, `conditional`, `hypothetical`, `question` |
| `commitment` | yes | the **source's** certainty: `certain`, `probable`, `possible`, `unknown` |
| `attribution` | yes | `{"mode", "claimant", "claimant_kind", "via"}` |
| `basis` | yes | `explicit` (the words state it), `inferred` (you concluded it) |
| `predicate` | for `statement` only, and required there | the shortest verb phrase from the text that states the relation, as written |
| `object_text` | no (statements) | exact text of a non-entity object, from inside `evidence` |
| `title` | no (employment) | exact text of a job title, from inside `evidence` |
| `correction` | no | `{"kind", "cue", "earlier_statement"}` |
| `allegation` | no | `true` if the passage presents it as an allegation or disputed claim |

### Relations and roles
| `relation` | Roles (`role`) | Participant `kind` |
|---|---|---|
| `employment`: a person works, worked or will work for an organisation | `employee`, `employer` | employee `person`; employer `organization` |
| `reporting`: a person reports to another person | `report`, `manager` | both `person` |
| `statement`: anything else that can be put as subject–predicate–object | `subject` (required), `object` (optional) | `person`, `organization` or `unclassified` |

**Participant rules:**
- **`text`:** exactly as written inside `evidence`, and occurring exactly once there.
- **`kind`:** `person`, `organization` or `unclassified`. (The spelling here is the referent type's,
  `organization`; claimant kinds below use `organisation`.)
- **`is_pronoun_or_vague`:** `true` for a pronoun ("she", "they"), a vague reference ("a senior manager", "the
  firm"), or a name you cannot tie to one individual. GUPI then sets the assertion aside rather than guess an
  identity. That is the correct outcome, not a failure.
- **Statements:** only a **named** entity (a person, organisation, named group or named system) is a
  participant. A descriptive object goes in `object_text`, or stays in the evidence.

### Times
- **`text`:** the time words exactly as written, inside `evidence` ("in March 2024", "since 2021", "on 3 May").
  Never a date you worked out.
- **`kind`:**
  - **`start`:** the state began then.
  - **`end`:** it ended then.
  - **`holds-since`:** it has held from then until the time of writing. This is not a start.
  - **`holds-at`:** it held at that time. Use it for an event on a day, too.
- **No time words:** give `[]`.

### Attribution
| Field | Values |
|---|---|
| `mode` | `direct` (the author asserts it), `reported` ("X said", "according to X"), `quoted` (verbatim quotation), `forwarded` (inside a forwarded message), `rumour` ("word is", "I hear"), `unattributed` ("it is understood that") |
| `claimant` | who originally made the assertion, **exactly as written in the passage**, or `null` when it is the author's own assertion, or when no claimant is named |
| `claimant_kind` | with a claimant: `person`, `organisation` or `unknown`; `null` without one. Use `person` or `organisation` **only when the passage establishes it**; otherwise `unknown` |
| `via` | intermediaries named in the passage between the author and the claimant, exact text, nearest first; usually `[]` |

**Forwarded text:**
- **The marker:** a forwarded block starts with a line like `---- Forwarded message ----`.
- **Inside the block:** an assertion there is `forwarded`.
- **Its claimant:** the sender in the block's `From:` header (or `null`), with `claimant_kind` `unknown` unless
  the passage says what the sender is.
- **The forwarder:** the person forwarding is the author, not the claimant.

### Corrections
| Field | Values |
|---|---|
| `kind` | `corrects`, `retracts`, `updates`, `contradicts` |
| `cue` | the exact words that signal it ("Correction:", "Scratch that") |
| `earlier_statement` | `null` |

**Never name or describe a target.** GUPI matches the correction to an earlier passage in the same thread. If
it cannot establish exactly one target, it keeps the correction unresolved for a human reviewer.

## A problem
`{"kind", "evidence", "detail"}`:
- **`kind`:** `unsupported-domain` (an assertion GUPI's relations cannot express), `ambiguous-reference`, or
  `insufficient-evidence`.
- **`evidence`:** the exact text, or `null`.
- **`detail`:** a short explanation.

Problems are how you report what you saw but did not turn into an assertion.
