# Integrity: what TypeDB enforces, what the application must check, and proposed schema additions

Date: 2026-11-03. Status: **Phase 6A analysis.** The schema additions in §3 are **proposed only, not
applied**; no migration file exists for them.

## 1. Enforced by TypeDB (3.14.1)
These are refused at write time, and the transaction fails as a whole. The two cardinality facts and the
enumeration fact were re-checked on 2026-11-03 against TypeDB CE 3.14.1 with a disposable database.

| Integrity rule | Mechanism | Already used for |
|---|---|---|
| A type exists, and a player may play the role | schema `relates` / `plays` | claim roles (`employment: employee/employer`) |
| Value types | attribute value types | dates as `datetime-tz`, confidence as `double` |
| Closed vocabularies | `@values(...)`; a value outside is refused | `verdict`, `valid-to-basis`, `time-precision`, `extraction-basis`, `polarity` |
| Numeric range | `@range(...)` | confidence 0..1 |
| Unique ids | `@key` | `gupi-id` everywhere |
| At most one value per owner | an `owns` defaults to `@card(0..1)`; a second value is refused | one of each valid-time bound per claim |
| Several values when wanted | explicit `@card(0..)` | (proposed for transmission, §3) |
| Fixed numbers of role players | `@card` on `relates` | identity `same @card(2..2)`, `alternatives` |
| References exist | a relation can only link stored things | evidence, supersession, extraction-output |
| Belief status computed one way | TypeQL functions | `believed_claim`, `hypothesis_claim`, `in_force_supersessions` |
| All or nothing | transactions | one batch per ingest |

## 2. Application-level validation (TypeDB cannot, or should not, decide)
| Rule | Why not TypeDB | Where |
|---|---|---|
| A passage, mention or time phrase equals the observation's text at its offsets | there is no substring comparison between attributes | `formation.validate`; `extraction.contract` |
| Window order (earliest ≤ latest) and start not after end | there is no declarative constraint across two attributes | `formation.validate` |
| "Since" is not a start (`since-as-start`) | a linguistic judgement about the source text | `formation.validate` |
| Ids and proposition keys | hashes of content, computed before writing | `gupi.ids`, `records` |
| The candidate format version | a property of the payload, not the store | `formation.validate` |
| Reading time phrases into windows | language and tense | `gupi.timeexpr` |
| Friendly checks before writing: known claim types, roles, player kinds, attributes | TypeDB would refuse these too, but only by failing the transaction, without a per-item reason. The checks run first so rejections can be reported item by item. | `SchemaInfo` checks in both validators |
| Answer semantics (v1, v2) | reasoning over evidence, deliberately in tested Python (ADR 0009) | `answering`, `answering_v2` |

A rule TypeDB can enforce is also checked in the application when that gives a better per-item report. The
application never relies on its own check alone where TypeDB can enforce the rule.

## 3. Proposed additive schema (core/0011, **not applied**)
These additions will be needed when candidates are stored (6B) and formed into claims (6C):
- Every change is additive: new types, or new `owns` and `plays`.
- No existing attribute, type or migration changes.
- Existing claims, their ids and their proposition keys stay as they are. New claim attributes would enter
  an id only when set, as `basis` and `polarity` already do.

```text
# claims: keep what formation knows about time, modality and attribution
attribute valid-from-basis, value string @values("stated", "lower-bound", "unknown");
attribute modality, value string @values("actual", "planned", "required", "permitted", "requested",
                                         "conditional", "hypothetical", "question");
attribute commitment, value string @values("certain", "probable", "possible", "unknown");
attribute attribution-mode, value string @values("direct", "reported", "quoted", "forwarded", "rumour",
                                                 "unattributed");
attribute transmission, value string @values("forwarded", "transcribed", "paraphrased", "excerpted",
                                             "authenticity-unclear");
claim owns valid-from-basis, owns modality, owns commitment, owns attribution-mode,
      owns transmission @card(0..);
relation assertion, relates asserter, relates asserted, relates via @card(0..);  # who said it, and through whom
referent plays assertion:asserter, plays assertion:via;
claim plays assertion:asserted;

# candidates: stored apart from claims; never believed, never answered from
attribute ir-version, value string;
attribute candidate-payload, value string;   # the exact gupi.candidate JSON (lossless round trip)
entity memory-candidate,
  owns gupi-id @key, owns ir-version, owns candidate-payload, owns method, owns recorded-at,
  owns proposition-key, owns polarity;        # indexed copies, for finding candidates about a proposition
relation candidate-of, relates candidate, relates observation;
relation candidate-relation, relates from, relates to, owns reason;  # corrects / updates / ... (kind in reason)
relation formed-into, relates candidate, relates claim;              # 6C: which claim a candidate became
memory-candidate plays candidate-of:candidate, plays candidate-relation:from, plays candidate-relation:to,
                 plays formed-into:candidate;
observation plays candidate-of:observation;
claim plays candidate-relation:to, plays formed-into:claim;
extraction-run plays extraction-output:run;  # unchanged; candidates join it as outputs
memory-candidate plays extraction-output:output;
```

**Design choices to confirm in 6B:**
- **Payload plus indexed copies.** The JSON payload is the exact record, so it round-trips losslessly. The
  indexed attributes exist only for querying.
- **A full breakdown** of times, participants and relations into separate TypeDB types is possible later, if
  queries need it.
- **`valid-from-basis = lower-bound`** keeps the "since" distinction on the claim itself after formation.
  The bounds alone already behave correctly under v2 (candidate-ir.md §5), but without this attribute the
  reason would be lost.
- **Corrections stay review-gated.** A `corrects` relation from a candidate becomes a *suggestion*. A
  supersession is still created only by `Memory.supersede` (ADR 0006).

**Compatibility and rollback:**
- Additive only.
- Rolling back means restoring the pre-migration export (ADR 0004). That is safe only while no candidate or
  new attribute has been written.
- v1, v2, the benchmarks and the budget ledger (`gupi-ledger`, a separate database) are unaffected.
