# Independent evaluation pack: brief for an outside author

**Who should write this:** a person or tool that has not seen GUPI's code, fixtures or results. **Do not share this
repository with them.** Give them only this page.

## The task
Write invented chat conversations, and questions about them, to test long-term memory. Everything is fictional. Use no
real people or organisations, and no text from existing benchmarks.

## What to produce
Between 8 and 15 sessions, spread over several simulated months, between a few recurring speakers, and at least **30
questions**, answerable only by connecting information:
| Category | At least | What it should test |
|---|---:|---|
| `provenance` | 10 | who said it, who disputes it, what is second-hand rumour, what was alleged but never established |
| `identity` | 10 | two different people with one name; a nickname; someone changing jobs; the same person referred to differently in separate sessions |
| `temporal` | 10 | what was true when; what stopped being true; corrections; a retraction; whether two things overlapped |

Prefer questions where looking up a name is not enough. Include some whose right answer is "unknown" or "disputed".

## Format
One JSON file:
```json
{"format": "gupi.phase8c-pack/1", "author": "who wrote it", "author_saw_gupi": false,
 "sessions": [{"id": "s1", "turns": [{"id": "s1t1", "speaker": "Name", "at": "2024-03-01T09:00:00Z", "text": "..."}]}],
 "questions": [{"id": "q1", "category": "identity", "question": "...", "answer": "...", "evidence": ["s1t1", "s4t2"]}]}
```
Each question's `evidence` lists every turn needed to answer it. The file is frozen, by hash, the moment it is received.
