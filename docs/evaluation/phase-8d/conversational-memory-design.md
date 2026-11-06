# Phase 8D.3: conversational memory modelling

**Design only. Nothing here is implemented.** All measures are read-only counts on the two development conversations, using
manual extraction. They show what might be worth building, and do not show that it would help.

## The question
Can GUPI represent what actually matters in a person's life: learning pottery, restoring an old boat, moving city, losing a
job? Phase 8C found subjects like these are what people talk about, and the claim model keeps them only as text.

## What the data says
| Measure | Result |
|---|---:|
| Claims linking two named things | 5 of 133 (3.8%) |
| Claims with object text | 125 of 133 |
| Claims touching a word that recurs across a speaker's sessions | **60 of 133 (45%)**, 26 of them on gold turns |
| Words recurring across sessions | 30 of 188; the most frequent appears in 8 sessions |
| Stated "my <relation> <Name>" in 788 turns | **0** |
| Temporal questions whose every gold turn has a dated event | 15 of 63 |

**Reading this:** the 45% is an upper bound from naive word overlap, and some recurring words are noise. But named links and recurring
subjects differ by about twelve times. **The structure is in what people do, not who they name.** Two other findings:
- **P2 reaches no development data.** It's correct, but friends don't introduce each other's relatives by relation and name. bare family references appear;
  named ones don't. That's P3, which stays deferred.
- **A subject that recurs isn't automatically a useful connection.** Connecting all of someone's "boat" claims may simply rebuild a keyword
  search.

## What needs representing
| Concept | Example | Today | The gap |
|---|---|---|---|
| Activity or interest | learning pottery | statement with text | no thing to connect |
| Ongoing project | restoring an old boat | scattered statements | no progress across sessions |
| Personal experience | ran a marathon | **event, with P4** | none for dated ones |
| Change in circumstances | lost a job | employment `end`, if an employer is named; otherwise text | unnamed employers |
| Unnamed people | "my sister" | stopped | P3, deferred |
| Events tied to activities | bought a kiln | event, unconnected | the link to the activity |

## Two approaches
**A. Extend the existing claim model.** No new concept. Normalise `object-text` into a stored key, so claims about "pottery" share something.
**B. A few reusable memory concepts.** One new referent kind, `activity`, as the thing a person pursues, plus one typed state `engagement`
(person, activity). Events and statements then point at the activity as their object.

| | A. Extend claims | B. Small concepts |
|---|---|---|
| **Example** | `statement(Juno, "bought", text: "a kiln")` plus a key `pottery` | `engagement(Juno, Pottery)` starts; `event(Juno, bought a kiln for, Pottery)`; `event(Juno, stopped, Pottery)` |
| **Schema** | one attribute | one entity, one relation, one migration, additive |
| **Parser and prompt** | a normalising step in code | one relation, one participant kind |
| **Evidence integrity** | strong: nothing new is asserted | strong if each claim still cites its quote, and an activity stays a label, never a fact |
| **Identity risk** | low: a shared key is only a text match, and easily wrong | **the main risk:** is "ceramics" the same as "pottery"? Same-name rules must apply, per person, with hypotheses for near matches |
| **Temporal** | none: text has no state, so "still learning?" can't be asked | **strong:** `engagement` reuses spells unchanged, so start, pause and stop work, and a pause is a real gap |
| **Questions it can answer** | "what did Juno say about pottery?" | also "is Juno still doing it?", "when did it start?", "what happened along the way?" |
| **Retrieval value** | likely low: mostly repeats keyword search | **unknown.** Possibly low for recall. The value, if any, is in answers |

## Recommendation
**B, kept deliberately small, and only behind a free test.** A adds a key that mostly restates keyword search. B adds the thing keyword search can't do:
reasoning about how something changed. It also reuses the most trusted part of GUPI, the temporal model, rather than adding a second one.

**Sketch, not a commitment:**
```
activity sub referent                            label as written; scoped to one person; never merged by similarity
engagement sub claim (participant, activity)     a state: starts, ends, gaps, using today's spells
event-statement (…, object: activity)            what happened along the way
```
**What it deliberately leaves out:** goals, sentiment, a general ontology, automatic topic linking, and ranking changes.

## A test before building it
Do this first, by hand, on a development conversation, for free:
1. **Label activities** in one conversation with the sketch above, in private lines, and record the effort.
2. **Replay as a dry run** with a test schema, and ask: how many activities, how many spells, how many ambiguous merges?
3. **Answer by hand** ten "still doing it?" questions from structure alone, and compare with raw text.

**Continue only if** the structure answers questions raw text handles poorly. **Stop if** activity boundaries need judgement calls so often that
they become a new source of false memories. This is an extraction contract problem before it's a schema problem.

**Do not assume** more graph means better memory. Phase 8C showed a populated graph can add nothing, and a fixture can hide that.
