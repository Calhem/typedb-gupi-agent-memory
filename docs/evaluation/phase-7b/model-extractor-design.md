# Proposed design: `model:candidate-v1` (design identifier only; not implemented)

**The principle:** the model reads and proposes, and deterministic code locates, measures, validates and
decides.
- **What the model may provide:** only what requires reading comprehension (which relation, which words,
  which modality).
- **What it never provides:** offsets, dates, ids, relation targets or anything else that code can compute
  or check.

## Pathway
```
observation text ──► model (structured output, schema-constrained JSON; no offsets, no dates)
                         │
                         ▼
             grounding (code): locate every quoted string exactly ──► grounding failures → extractor outcomes
                         │
                         ▼
             normalisation (code): offsets, timeexpr windows, forwarded regions, pronoun check (rules:v2.1 list),
                                   correction targets resolved against the thread and the store
                         │
                         ▼
             gupi.candidate/1 CandidateSet  (extractor = "model:candidate-v1:<model id>:<prompt hash>")
                         │
                         ▼
             validate(cset, observation, schema=LIVE SCHEMA)   ◄── requires C1 fixed first
                         │
                         ▼
             store.submit ──► formation:v1 decision (formed / withheld / review / rejected); nothing else changes
```

## Model output (the proposed JSON schema, abridged)
```json
{
  "outcome": "assertions | no-relevant-assertion | invalid-input",
  "assertions": [{
    "evidence": "exact text copied from the message",
    "evidence_occurrence": 1,
    "relation": "employment | reporting | statement",
    "predicate": "for statements: a few words, copied where possible",
    "participants": [{"role": "employee", "text": "Mara Quist", "kind": "person | organization | unclassified",
                      "is_pronoun_or_vague": false}],
    "title": "interim CFO",
    "times": [{"text": "since last month", "kind": "start | end | holds-since | holds-at"}],
    "polarity": "positive | negative",
    "modality": "actual | planned | required | permitted | requested | conditional | hypothetical | question",
    "commitment": "certain | probable | possible | unknown",
    "attribution": {"mode": "direct | reported | quoted | forwarded | rumour | unattributed",
                    "claimant": "Dana Okoro", "via": ["Ivo Marsh"]},
    "correction": {"kind": "corrects | retracts | updates | contradicts", "cue": "Correction:",
                   "earlier_statement": "text of the statement corrected, if quoted"},
    "allegation": false,
    "basis": "explicit | inferred"
  }],
  "problems": [{"kind": "ambiguous-reference | unsupported-domain | unreadable-time | insufficient-evidence",
                "evidence": "exact text", "detail": "short reason"}]
}
```

**Every enumerated field is required, with no defaults.** The contract's defaults are the least cautious
values (finding C8), so an omitted field must fail, not default to certain or direct.

**Why the contract itself is not prompted:** the model is not shown `gupi.candidate/1`. A narrower,
text-only schema keeps it away from fields it must not set.

The example values above are developer-authored, for illustration.

## Deterministic steps after the model
| Concern | Rule |
|---|---|
| **Source grounding** | `evidence` must occur exactly in the message. If it occurs more than once, `evidence_occurrence` selects one. If that is missing or out of range: outcome **ambiguous-span**, with no candidate; never pick the first silently. Whitespace-normalised matching is allowed only if it maps back to one exact span. Every other quoted string (participants, times, claimant, via, cue) must occur **inside** the evidence span, or in the message for the claimant and via. Otherwise: **grounding-failure**. |
| **Offsets** | computed by code from the located strings. The model's text is never trusted for positions. |
| **Entities** | Surfaces exactly as written: no invented names. A participant in the rules:v2.1 pronoun list, or one marked `is_pronoun_or_vague`, gives outcome **ambiguous-reference** with no candidate. **v1 forms no pronoun-resolved candidates at all**; the model may name a candidate antecedent in `problems` for scoring only. Same-named people are not merged by the extractor; referent resolution stays with formation (S8 applies unchanged, and is scored as a representation limit). |
| **Time** | The phrase is located and read by `gupi.timeexpr` against the observation time, so the model never supplies a date. `holds-since` is never converted to `start` (the validator already refuses "since" as a start). Unknown years and relative phrases keep their `assumption`. Unread phrases keep precision `unknown`, and formation sends them to review. |
| **Attribution** | `claimant` → `asserted_by` (must occur in the message); `via` → intermediaries. Text inside a forward marker (the rules:v2 `FORWARD` regions) is forced to mode `forwarded`. A model that says `direct` there is recorded as an attribution disagreement. Repeats of an earlier candidate are marked `repeats` by code (the rules:v2 `_same_statement` logic), so formation withholds them. |
| **Modality and polarity** | taken from the model, but validated against the enums. Cue cross-checks are recorded, never applied: "might", "will", "if", "denies" and "not" against a model choice of `actual`, `certain` or `positive` are flagged for scoring, and the candidate is unchanged. |
| **Corrections** | code resolves the target among earlier candidates in the thread (same proposition and boundary), and formation lists claim targets in the store as a suggestion. **Nothing is retracted or superseded.** If a correction has no resolvable target, the candidate still goes to review. How to express that within the contract is an open decision (stage-2-plan.md, decision D3). |
| **Allegations** | no contract field exists (C4). They are kept in the extractor's report for scoring; the candidate uses mode `reported` or `unattributed` and the source's commitment, as the model judged them. |

## Extractor outcomes, versus formation outcomes
**Extractor outcomes** are recorded in the extractor's report, like rules:v2.1's rejection reasons. They are
**not** candidates and never reach the store:

| Outcome | Meaning |
|---|---|
| `no-relevant-assertion` | the model found nothing (also the correct result for negative controls) |
| `unsupported-domain` | an assertion that cannot be expressed as employment, reporting or statement |
| `ambiguous-reference` | a pronoun or vague participant, or an unclear identity |
| `ambiguous-span` | evidence that occurs more than once, with no valid occurrence given |
| `grounding-failure` | a quoted string that is not in the message |
| `unreadable-time` | recorded when `timeexpr` cannot read the phrase. The candidate is still produced (precision unknown, so formation reviews it) |
| `insufficient-evidence` | the model judged the text too vague |
| `invalid-model-output` | the JSON failed the schema, or there was a refusal, a truncation or an empty response |
| `extraction-error` | a transport or other failure. Recorded, never silently empty |

**Formation outcomes** come after validation, and are the store's existing decision records:
- **rejected:** malformed or unsupported
- **withheld**
- **review**
- **formed**

**A candidate that fails validation is a formation rejection,** not an extractor outcome. The two are
counted separately.

## Contract preconditions (Stage 2, each needing approval)
1. **Fix C1** (schema-aware validation of `statement` attributes). This is a production change with its own
   test; `tests/integration/test_contract_c1.py` is the strict expected failure that demonstrates it.
2. **Make the model path call `store.submit` with the live schema.** This is a caller choice, not a contract
   change.
3. **Decide D3** (the representation of an unresolved correction target).

**Out of scope for `model:candidate-v1`:** fixing C2 (organisational claimants) and adding allegation
semantics (C4). They are scored as representation gaps, not model errors.
