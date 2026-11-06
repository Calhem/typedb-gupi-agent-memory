# Independent evaluation pack: brief for an outside author

**Who should write this:** a person or tool that has not seen GUPI's code, fixtures or results. **Do not share this
repository with them.** Give them only this page.

## The task
Write invented chat conversations, and questions about them, to test long-term memory. Everything is fictional. Use no
real people or organisations, and no text from existing benchmarks.

## What to produce
Between 8 and 15 sessions, spread over several simulated months, between a few recurring speakers, and at least **60
questions**, answerable only by connecting information:
| Category | At least | What it should test |
|---|---:|---|
| `relationship` | 10 | who is related to whom, including people never named ("my sister"), and two different people sharing a name |
| `temporal` | 10 | what was true when; the order things happened in; whether two things overlapped |
| `conflict` | 10 | sources that disagree; a correction; a retraction; which version still stands |
| `historical-change` | 10 | a job, home or circumstance that changed; what was true before and after; what stopped being true |
| `provenance` | 10 | who said it, what is second-hand rumour, what was alleged but never established, what is merely uncertain |
| `activity` | 10 | an ongoing project or interest: how it started, progressed, paused or ended, across sessions |

Prefer questions where looking up a name is not enough. Include some whose right answer is "unknown" or "disputed".
Write the conversations the way people talk: mostly first person, few full names, and plenty of "my sister" and "the project".

## Format
One JSON file:
```json
{"format": "gupi.phase8c-pack/1", "author": "who wrote it", "author_saw_gupi": false,
 "sessions": [{"id": "s1", "turns": [{"id": "s1t1", "speaker": "Name", "at": "2024-03-01T09:00:00Z", "text": "..."}]}],
 "questions": [{"id": "q1", "category": "identity", "question": "...", "answer": "...", "evidence": ["s1t1", "s4t2"]}]}
```
Each question's `evidence` lists every turn needed to answer it. The file is frozen, by hash, the moment it is received.
