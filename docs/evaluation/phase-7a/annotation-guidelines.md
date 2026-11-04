# Phase 7A annotation guidelines: domain and failure classifications

These are the rules used to label `annotations.json`. The labels were written before `rules:v2` ran on any
sampled turn. There is one annotator, the implementer, with no adjudication.

## Unit of annotation
- **The unit is a fact, not a turn.** A turn can hold several facts, each labelled separately. A turn with
  none is category C.
- **A fact is a potentially useful memory:** a durable assertion about a participant, a third party or the
  world that an agent might later be asked about. It can be stated or presupposed.
- **What is not a fact:**
  - greetings, thanks and praise
  - questions that presuppose nothing new
  - generated content the user asked for (recipes, tweets, translations, documents)
  - pasted material the user does not assert
- **Presuppositions:** a durable fact presupposed by the other speaker counts. For example, "How do you stay
  inclusive in your work as an artist?" presupposes the addressee is an artist. It is marked `implicit`, and
  usually needs `cross-turn`.
- **Text:** labels are short descriptions. No dataset text is copied beyond a few words of common phrasing.

## Domain categories
| Category | Rule | Examples |
|---|---|---|
| **A** supported domain | The fact is one of `rules:v2`'s claim types and roles: employment (a person joins, works at, leaves or is appointed at an organisation) or reporting (a person reports to a person), or a correction of one of these | "the new Senior Marketing Manager at [named company]"; "lost my job"; "got a temp job" |
| **A?** borderline | Plausibly employment, but not cleanly: running one's own business, a role at an unnamed institution, a career intention without an employer | "my store", "my dance studio", "my teaching assistantship" |
| **B** representable, unsupported | No typed claim exists. Representable only as the provisional generic `statement` claim (core/0003: subject referents, `predicate-text`, optional object or `object-text`, valid time), so typing and constraints are lost. World knowledge is B, with domain `world knowledge` | hobbies, family, plans, purchases, residence, education, events, opinions, book authorship |
| **C** nothing relevant | The turn holds no fact as defined above | "Wow, what a fun moment! What's the band?" |

**How representability was checked:** against the schema in TypeDB (`employment`, `reporting`,
`statement`, `identity`; referent kinds person, organisation, unclassified) and the candidate contract
(`gupi.formation.validate`: the claim types and roles the schema offers; every participant needs a surface
span in the passage).

**Three problems with representing these facts, recorded per fact:**
- **Unnamed employers:** an A fact with an unnamed employer has no surface to stand for the employer, so
  representing it would need a placeholder referent. The contract defines none, and GUPI's "never invent"
  rule argues against it.
- **Weak fit:** preferences and plans fit `statement` only weakly.
- **Not participant memory:** world knowledge fits `statement`, but it is not memory about the conversation's
  participants.

## Fields
| Field | Values |
|---|---|
| `about` | speaker, addressee, user, third party or parties |
| `explicit` | explicit (stated) or implicit (presupposed or implied) |
| `needs` | cross-turn (an earlier turn is needed), pronoun, relative time, duration, dates |
| `stage` | the earliest expected failure category (below), or "2\|3" when the A/B boundary is ambiguous |

## Failure categories (earliest applicable)
| # | Category | Rule used |
|---|---|---|
| 1 | Input missing or corrupted | the adapter's text differs from the raw turn, or is empty or truncated by the pipeline (raw-data truncation is noted, not counted) |
| 2 | Outside the implemented domain | category B |
| 3 | In-domain, unsupported vocabulary or syntax | category A, where the phrasing matches no `rules:v2` pattern (including an unnamed employer, which no pattern accepts) |
| 4 | Cross-turn context required | the fact is in the domain and phrased supportedly, but needs an earlier turn |
| 5 | Pronoun or entity resolution required | as 4, but for a pronoun or alias |
| 6 | Temporal interpretation unsupported | the fact would be extracted, but its time phrase cannot be read |
| 7 | Attribution, modality or correction structure unsupported | as 6, for these structures |
| 8 | Extracted, rejected by validation | observed from the extractor's report or `store.submit` |
| 9 | Extracted, withheld or sent for review | observed from the store |
| 10 | Formed | observed from the store |
| 11 | Other | with an explanation |

**How the categories were applied:**
- **Ordering:** domain comes first, then linguistic coverage, then context, then formation. Secondary needs
  (4–7) are recorded in `needs` even when 2 or 3 comes first.
- **Observed or annotated:** stages 8–10 are taken only from what the store recorded, never from the
  annotation. In this sample no candidate appeared, so none occurs.

## Known weaknesses
- **One annotator, who built the extractor:** domain boundaries, especially A?, are judgements.
- **Generous counting:** "potentially useful memory" includes low-value plans and opinions.
- **Long assistant turns:** they were read in full only where they contained first-person or "you
  mentioned" content. The rest is generic advice.
