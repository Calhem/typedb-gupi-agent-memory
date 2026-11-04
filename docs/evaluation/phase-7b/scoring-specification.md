# Scoring specification

**Scoring is deterministic wherever possible. No LLM judge is used at any point.**
- **Where semantic equivalence cannot be decided by rule:** a human adjudicator decides it, from a
  generated list, and each decision is recorded.
- **What the result keeps:** every per-assertion and per-passage result is kept.

## Units and denominators
- **Gold unit:** an adjudicated gold assertion (annotation-guidelines.md). Alternatives of one ambiguous
  assertion form a group, and the group counts once.
- **Prediction unit:** a candidate (or, for coverage only, an extractor outcome) for a passage.
- **Sets:** S1 and S2 are always scored and reported separately. DEV is never scored as evidence.
- **Reporting:** every metric is reported as *k / n* with a 95% Wilson interval.

## Matching a candidate to a gold assertion
Matching is in this order and one-to-one: each gold group and each candidate is used at most once, with the
best tier first.

| Tier | Rule |
|---|---|
| **exact** | same passage; the candidate's passage span overlaps the gold span; `claim_type` equals `gupi_claim_type`; every gold participant role has a candidate participant with the same role and the same surface after normalisation (casefold, collapsed whitespace, a leading "the", a trailing "'s"). For statements, the normalised predicates are also equal |
| **partial** | same passage, overlapping span, same claim type, and at least one participant role equal, but not all; or a statement with equal participants but a different predicate |
| **adjudicated** | any pair left over that overlaps in span within a passage goes to the adjudication sheet. A person (not the developer) marks it *equivalent*, *partial* or *different*, with a one-line reason. Only *equivalent* counts as a match |

**Recall and precision:**
- **The headline:** recall and precision count exact plus adjudicated-equivalent matches.
- **Reported separately:** partial matches.
- **Pronouns:** a candidate whose participant is a pronoun never matches a gold participant written as a
  name.

## Metrics
| Dimension | Metric | Denominator |
|---|---|---|
| Coverage | precision = matched / candidates; recall = matched / gold groups; F1 | candidates; gold groups |
| Domain | recall separately for gold `employment` / `reporting` (in the domain), `statement`, and `none` (not representable: is it reported as `unsupported-domain`?) | gold groups of each kind |
| Entities | participant accuracy (every surface right) and role accuracy (the roles right, given the surfaces) | matched pairs |
| Attribution | mode accuracy; claimant accuracy (surface equal, or both blank); `via` accuracy; **false independent corroboration** = gold `independent_origin = no` (or mode forwarded) predicted as direct or independent | matched pairs; gold non-independent assertions |
| Time | expression preserved (phrase equal after normalisation); kind accuracy; window accuracy (code-read window equals the gold window, where gold gives one); **invented precision** = predicted window narrower than gold, or a window where gold has none | matched pairs that have a time in gold or in the prediction |
| Modality | polarity accuracy; modality accuracy; commitment accuracy; **unsupported certainty** = predicted `certain` (or mode `direct`) where gold is weaker | matched pairs |
| Corrections | detection recall (gold relation present → candidate relation, or a correction cue, present); target accuracy (the resolved target equals the gold target, when gold names one) | gold assertions with a relation |
| Grounding | exact-span validity (grounded / produced); grounding-failure, ambiguous-span and invalid-output rates; **unsupported claims** = unmatched candidates the adjudicator marks *not supported by the text* (as opposed to *gold omission*); **invented entity** = a participant surface absent from the passage, or present but not a referent of the assertion in gold | produced candidates or model assertions |
| Formation | validated / withheld / review / formed / rejected counts; agreement of the formation outcome with gold `expected_admission`; **unsafe formations** = severe errors among *formed* candidates (formed without review) | candidates; matched pairs |
| Operations | latency per passage (p50, p95), throughput, input, output and thinking tokens, cost from the ledger's settled actuals | passages |

## Special cases
- **Ambiguous gold:**
  - **Matching:** a candidate matching any alternative in the group matches the group.
  - **Fields:** each field is correct if it equals the field of the alternative matched.
- **Duplicates:** a second candidate matching an already-matched group is a *duplicate*. It is counted
  separately, not as a false positive. Formation would withhold true duplicates only if marked `repeats`.
- **Abstentions:** an extractor outcome (`ambiguous-reference`, `insufficient-evidence`, `unsupported-domain`)
  whose evidence overlaps a gold span counts as **abstained**.
  - **For recall:** it is a miss.
  - **When it is appropriate:** it is reported as such when gold marks that assertion ambiguous, `?`
    resolved, or not representable.
- **Negative controls:** any candidate from a negative-control passage is a false positive, and an
  *unsupported claim* unless adjudicated otherwise.
- **Gold omissions:**
  - **What they are:** an unmatched candidate the adjudicator marks *supported by the text, missing from
    gold*.
  - **How they are handled:** they are counted, reported, and excluded from the precision denominator.
  - **What is never done:** the gold is not edited after freezing. A fresh corpus version would have to be
    frozen instead.

## Outputs
- **Raw results:** `per_assertion.csv` holds every gold group and every candidate, with the tier, every
  field's correctness and the formation outcome.
- **Per passage and summary:** `per_passage.json` and `summary.json`, with every metric as k / n and an
  interval, per set and per system.
- **The adjudication sheet:** the decisions are kept with their rationales.
- **The scorer version** (a source hash) goes into the manifest.
