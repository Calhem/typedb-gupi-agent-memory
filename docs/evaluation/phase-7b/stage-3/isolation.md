# Isolating the gold from the extraction session

**The requirement:** the Stage 3B extraction session must not have access to gold answers, annotation notes,
scoring outputs, or a scorer that reveals expected answers.

**Why a `private/` folder in this checkout is not enough:** a Claude Code session can read any file on the
machine unless prevented. So the material is split across three places, and the separation is **enforced
twice**: by the session's permissions, and by an audit of the session's own transcript.

## The three places
| Place | What it holds | Git | Readable by the 3B session |
|---|---|---|---|
| this repository (public on GitHub) | the passages, instructions, response format, scorer, manifest and these docs. **No gold, categories, notes or scored results** | pushed | no (denied) |
| the private folder, `gupi-stage3-private/` beside this repository | gold.jsonl, categories.json, annotation-notes.md, the corpus builder, the pre-freeze check, the baseline results | local history only, **no remote** | no (denied) |
| the extraction bundle, `~/gupi-stage3-extraction/` (outside both, and outside `~/Desktop`) | only `passages.jsonl`, `extraction-instructions.md`, `response-format.md`, `README.md`, `.claude/settings.json`, and an empty `responses/` | its own local history, **no remote**; it never contained gold | yes: this is its working folder |

**How the bundle was made:** by `stage3 bundle`, which copies the five public files and nothing else. Its
contents are hashed in manifests/stage-3a.json. A search of the bundle finds no gold, categories or notes.

**The scorer and the gold format:**
- **The scorer** (in this repository) contains no answers. Its synthetic test fixtures are unrelated to the
  corpus.
- **The gold format** (gold-annotation-contract.md) describes annotation rules, not answers.
- **Neither is in the bundle.**

## Enforcement 1: the session's permissions (`.claude/settings.json` in the bundle)
- **Allowed:** reading inside the bundle, and writing in `responses/`.
- **Denied tools:** Bash, web fetch and search, subagents, notebooks and Edit.
- **Denied reads:** `~/Desktop` (which holds this repository, the private folder and every other project),
  `~/Documents`, `~/Downloads`, `~/Library`, **`~/.claude`** (where every Claude Code transcript and memory
  lives, including the Stage 3A session that wrote the gold), `~/.config`, `/private`, `/tmp`, `/Volumes`,
  and the parent folder.
- **Denied connectors:** terminal, browser, Chrome, computer use, session management (which can search other
  sessions' transcripts), directory, host, registry, scheduling and visualisation.

## Enforcement 2: the transcript audit (`stage3 audit`), before any scoring
**What it reads:** every JSONL transcript the 3B session wrote, subagents included, and every tool call in
them.

**The run is invalid, and is not scored as valid, if any of these appear:**
- **a tool other than** Read, Write, Glob, Grep or TodoWrite (any Bash, web or connector call counts)
- **any file path outside the bundle**
- **a response file written more than once:** a regenerated output
- **no transcript at all:** nothing would prove the isolation

**What the audit catches:** anything the permissions miss. That includes a connector whose name is not
known in advance. Because the transcript records every tool call, the audit is the decisive check.

## What remains (see README.md, integrity risks)
- **Same model family:** the 3B session is the same model family that wrote the passages and gold. Isolation
  prevents it seeing the answers, but **it does not make the material independent.**
- **Hidden context:** anything Claude Code loads without a tool call is outside the audit.
  - **What was checked on 2026-11-04:** there is no `~/.claude/CLAUDE.md`, and the 3B folder has no project
    memory or CLAUDE.md.
  - **Before 3B:** check the session start shows no other memory.
- **The cloud alternative:** running 3B in a cloud session, against a private GitHub repository holding only
  the bundle, would remove the shared machine entirely. That needs the owner to create the repository, so it is
  an option, not the default.
