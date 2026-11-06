# Annotation manual: activities in a conversation

You will read one complete conversation between two people, and record the activities each person is involved in. Read everything first. Then write your annotations.

**Your own judgement is what is wanted.** There are no target numbers. Being careful matters far more than being complete, and saying "unclear" is a good answer.

## What to record
**An activity** is something a person does, pursues or is involved in over time: a hobby, a job, a project, a practice, an interest they act on.
Three things are easily confused, so keep them apart:
- **The activity itself:** the thing being pursued.
- **An event involving it:** one thing that happened, once.
- **Being engaged in it:** the person is actually doing it at some time.

**Never assume that repeated words mean the same activity.** Two mentions belong together only if you are satisfied that they concern the same thing, for the same person. If two things might be one or might be two, keep them apart and say so.

## For each activity
| Field | Meaning |
|---|---|
| `id` | any short id you like |
| `person` | exactly as the speaker is named in the conversation |
| `label` | a short description, in your own words |
| `basis` | `explicit` if the conversation states the person's involvement; `inferred` if you concluded it |
| `final_state` | at the end of the conversation: `engaged` only if the last evidence directly says it still continues then; `ended` if it is stated to be over; `unknown` if nothing says; `contradictory` if the evidence conflicts |
| `mentions` | every mention, as below |

## For each mention
| Field | Meaning |
|---|---|
| `turn` | the turn id without the conversation name, such as `D3:2` |
| `quote` | words copied exactly, character for character, from that turn. Keep it short |
| `role` | one of the roles below |
| `link` | `clear`: certainly this activity. `probable`: likely. `unclear`: can't say |
| `time` | the time words, copied exactly, or `null`. Never work out a date |

| Role | Use when the words say |
|---|---|
| `start` | it began |
| `resume` | it began again, after stopping |
| `end` | it stopped |
| `past` | it used to happen, and is over |
| `engagement` | the person is doing it, at the time of speaking |
| `negated` | it is not happening, or has not happened |
| `event` | one thing happened, involving it |
| `plan` | an intention, or something not yet happened |
| `reference` | it is mentioned, without saying any of the above |

**Silence means nothing.** Never decide that something continued, finished or was abandoned because it stopped being mentioned. A plan is not an event. An offer is not a start.

## Also record
- **`not_same`:** pairs of activities that someone could easily merge but you kept apart, and why.
- **`contradictions`:** places where the conversation appears to conflict with itself about an activity, whatever the explanation. Give the activity ids, the turns and a short note.
- **`review`:** anything a careful person should check, as a question.

## Neutral example (invented)
> [D1:1] Juno, 2024-01-05: I started learning to sail last spring.
> [D2:1] Juno, 2024-03-01: Sold my boat, so no more sailing for me. My sister sails though.
> [D3:1] Juno, 2024-06-01: Bought a kayak.

Juno's sailing has a `start` ("I started learning to sail last spring", time "last spring") and an `end` ("no more sailing for me"), and `final_state` `ended`. Selling the boat is an `event`. The sister's sailing is a different person's. The kayak is one `event`: it establishes no ongoing activity, and whether it replaced sailing is unclear.

## Output
Write one JSON file, exactly:
```json
{"reader": "describe yourself honestly", "activities": [{"id": "a1", "person": "Juno", "label": "sailing", "basis": "explicit", "final_state": "ended",
  "mentions": [{"turn": "D1:1", "quote": "I started learning to sail last spring", "role": "start", "link": "clear", "time": "last spring"}]}],
 "not_same": [{"a": "a1", "b": "a2", "why": "..."}],
 "contradictions": [{"activities": ["a1"], "turns": ["D1:1", "D2:1"], "note": "..."}],
 "review": [{"activities": ["a1"], "question": "..."}]}
```
