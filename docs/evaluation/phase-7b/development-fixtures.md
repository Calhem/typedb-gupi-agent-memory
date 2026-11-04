# Development fixtures (developer-authored engineering material)

**The labelling:** everything in `tests/fixtures/phase7b-dev/` was written by the developer. It is
engineering material for testing code. **It is not independent evaluation evidence,** and no result on it
may be described as one.

**Not used:** nothing comes from the specialist M1 branch, and it is unchanged.

| File | Contents | SHA-256 (offline set) |
|---|---|---|
| `offline/passages.csv` | 26 passages, set DEV, fictional people and organisations | `1a6f329f…1fcb9d` |
| `offline/assertions.csv` | 24 gold assertions, checked by hand by the developer (not independently annotated) | `4ed24a57…c5196a` |
| `offline/responses.json` | 26 hand-written, model-shaped responses (not model output); 10 deliberately faulty | `6ed5f048…a889de6e` |
| `passages.csv`, `assertions-A.csv`, `assertions-B.csv` | 2 passages for the Stage 1 annotation checker tests | — |

## Coverage
| Phenomenon | Passages |
|---|---|
| employment: join, start, promotion, departure, first person | 101, 102, 109, 119, 122, 124 |
| reporting, including negation | 103, 111, 120, 121 |
| ownership and other organisational relations (statements) | 104, 125 |
| allegations and investigations | 105, 123 |
| pronoun and attributed speech | 106 |
| forwarded evidence, and a repeated forwarded copy | 107, 108 |
| corrections, and a retraction | 109–110, 125–126 |
| contradictory sources | 120–121 |
| hedged certainty | 112 |
| conditional and hypothetical | 113, 114 |
| uncertain identity | 117 |
| approximate and relative dates | 118, 119 |
| negative controls | 115, 116 |

## The deliberately faulty responses (`responses.json` → `faults`), and what happens to each
| Passage | Fault | Handling |
|---|---|---|
| 106 | resolves "her" to Dana Okoro, says `inferred` | `inferred-not-admissible` |
| 108 | a forwarded copy called direct | forced to `forwarded`; formation forms it (F1) |
| 112 | omits the "I think" hedge, keeps `certain` | commitment downgraded to `unknown`, so review |
| 114 | a counterfactual called `actual` | `cue-conflict` |
| 115 | malformed JSON | `invalid-model-output` |
| 116 | an employment invented from praise ("everyone") | `ambiguous-reference` |
| 117 | completes "Dana" to "Dana Okoro" | `grounding-failure` |
| 119 | supplies "July 2025", which is not in the text | `grounding-failure` |
| 122 | includes offsets | `invalid-model-output` |
| 126 | a retraction whose target cannot be matched | `correction-target-unresolved` |

**Regenerating:** the fixtures were written once and are committed as data. Any change needs a new commit,
and the hashes above must be updated.
