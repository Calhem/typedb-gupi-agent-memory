# Manual extraction inside a Claude subscription

**What this is:** a way to populate GUPI's claim graph with no API, no key and no spending. Someone works through the
conversation in an interactive Claude session and saves the replies. GUPI then replays them through the same parser and
formation policy as any other extraction.

**What it is not:** a `gpt-4o-mini` result, or a route to automate anything. It doesn't use a programmatic API, and it won't
scale to a leaderboard. Its job is to let us study extraction and graph quality for free.

## Steps
1. **Export.** Development conversations only, and the command refuses a folder inside the repository:
   ```bash
   uv run python -I -m gupi.benchmarks.phase8c_manual export --conversations conv-30 --out ../gupi-phase8c-private/bundle-2
   ```
   This writes the rules and the turns. **It never includes questions or answers,** so the extractor stays blind.
2. **Extract.** In a Claude Code session or a claude.ai chat, give it `INSTRUCTIONS.md` and one conversation file. Work in
   batches of about 100 turns, and save each reply into a private `.jsonl` file. Output is one line per turn.
3. **Check.** This runs the lines through the unchanged parser, and says what stopped and why:
   ```bash
   uv run python -I -m gupi.benchmarks.phase8c_manual check --conversations conv-30 --responses ../gupi-phase8c-private/responses/conv-30.jsonl
   ```
4. **Evaluate.** Replay needs no model. Identical input gives identical claims:
   ```bash
   uv run python -I -m gupi.benchmarks.phase8c_eval run --set dev --conversations conv-30 --responses ../gupi-phase8c-private/responses/conv-30.jsonl --json OUT.json
   ```

## Rules that protect the result
| Rule | Why |
|---|---|
| Never show the extractor the questions | claims derived from an answer key would prove nothing |
| Extract whole conversations, chosen before looking at results | picking turns near gold would leak the answer |
| Write each line once | a repeated turn is an error, so a reply can't be quietly improved |
| Keep every file in `../gupi-phase8c-private/` | they quote the dataset; that folder has a local git history and no remote |
| Never run this on the frozen held-out conversations | the export and evaluation both refuse |
| Record who extracted | the source is stored on each candidate as `claude-subscription-manual:<file hash>` |

## The short format
The bundle explains it: `e` evidence, `p` participants, `pred` predicate, `obj` object text, `t` times, and so on. Anything
left out takes a stated default. `expand` turns each line into the exact `gupi.model-response/1.1` the parser takes.
