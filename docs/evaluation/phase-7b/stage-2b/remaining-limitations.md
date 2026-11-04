# Remaining limitations after Stage 2B

| # | Limitation | Why it is left | What would address it |
|---|---|---|---|
| S8 | Two same-named people in **one** conversation share a referent id (a strict expected failure in the C2 tests) | Referent ids are scoped by conversation, kind and surface, for every referent, not only claimants. The candidate carries no evidence that tells the two apart | A redesign of referent scoping (needs approval) |
| L1 | `rules:v2` and `rules:v2.1` still emit format 1.0, so their claimants are always `unclassified` | The brief forbids changing the extractors; absence of a kind is deliberately not taken as evidence | A later extractor version that states claimant kinds from cues |
| L2 | A null-target correction is never resolved automatically, even when one plausible target exists | A deliberate policy: the source does not establish the target, so a reviewer must (`store.assign_correction_target`) | Nothing; this is the intended behaviour |
| L3 | Assigning a target records it but supersedes nothing | Acting on a correction stays a separate, explicit memory operation | A reviewed "apply correction" step, if wanted |
| L4 | F1 copy detection needs the same passage words and the same claimant label (compared word by word) | A paraphrased forward, or a differently written sender name, is not recognised as a copy; it forms a claim. Recognising it would need identity resolution, which formation does not do | Reviewed identity groups feeding copy detection |
| L5 | Inferred statements from the offline interface are deferred, not reviewed | Policy kept: inference stays out of automatic formation. Formation now sends any candidate with `basis: inferred` to review (`6d4cda2`; no current extractor emits one). The interface still refuses a model's inferred assertion (`inferred-not-admissible`), because its typical form (DEV-106: "her" resolved to a name) is only representable by inventing an identity | Passing inferred assertions that need no identity resolution to review (needs approval; the brief adds no new inference) |
| L6 | The offline interface has been exercised only on developer-authored recorded responses | No model, API or download is authorised; these fixtures are not evaluation evidence | The independent corpus and a live model, when approved |
| L7 | The recorded developer responses are all format `gupi.model-response/1` | They are frozen inputs and must not change; format 1.1 responses are covered by unit tests only | New recorded responses, once approved |

**Blockers:** none. No schema migration, breaking contract change or redesign was needed for C2, D3 or F1.
