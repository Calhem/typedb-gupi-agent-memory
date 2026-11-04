# GUPI Stage 3B extraction bundle

This folder is everything an extraction session may see.

| File | Contents |
|---|---|
| `passages.jsonl` | the 32 passages: id, thread, turn, document kind, author, date, metadata, text, and the text's SHA-256 |
| `extraction-instructions.md` | the task and its rules (`gupi.stage3-extraction/1`) |
| `response-format.md` | the exact output format (`gupi.model-response/1.1`) |
| `responses/` | where the responses are written: one `<passage_id>.json` per passage |
| `.claude/settings.json` | the session's permissions: reading this folder and writing `responses/` only |

**Start by reading `extraction-instructions.md`, then `response-format.md`.**

**What this folder holds:** no answers, scoring code or evaluation results. Nothing outside it is needed.
