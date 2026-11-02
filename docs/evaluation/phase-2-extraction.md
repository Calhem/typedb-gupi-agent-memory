# Phase 2 extraction evaluation

Date: 2026-11-02. Data: synthetic, hand-annotated conversations in `tests/fixtures/conversations`
(people and organisations invented). Each conversation is extracted into its own disposable TypeDB
database and read back from TypeDB before scoring. Raw results: `rules-v1-dev.json`, `rules-v1-heldout.json`.

Reproduce: `uv run python -I -m gupi.evaluation --set heldout --extractor rules`

**These are results of the offline, rule-based extractor. They are not evidence of how an LLM extractor
performs; the Claude extractor has not been evaluated.**

## Protocol
- The held-out set was committed (`814f501`) before any extraction rules existed. The rules were written
  against the development set only, frozen at `7dcbff8`, and the held-out set was then run once. The rules
  have not been changed since; tests use only the development set.
- A claim counts as correct when its message, type, role players (by surface name) and attribute values
  all match the gold claim. Time is scored only on correct claims: start window, end window and
  "ongoing at observation" must all match.
- Small sets (12 messages, 12 gold claims each): these numbers show behaviour, not statistical accuracy.

## Results: offline rule extractor (`rules:v1`, no API calls)

| Set | Claim precision | Claim recall | Mention precision / recall | Time correct (of matched) | Basis |
|---|---|---|---|---|---|
| Development | 1.00 (11/11) | 0.92 (11/12) | 1.00 / 0.91 | 11/11 | 11 explicit |
| Held-out | 1.00 (6/6) | **0.50 (6/12)** | 1.00 / 0.50 | 6/6 | 6 explicit |

No claim was rejected by the validator, and no date was invented: the one assumed year ("in June", year
taken from the observation date) is recorded as a note on the claim's extraction run.

## Error taxonomy (held-out)
| Message | Gold claim | Error | Cause |
|---|---|---|---|
| h1-1 | employment (Jonas Berg, Lumen Labs, CFO) | missed | sentence structure: "Welcome X, who joined ..." |
| h1-3 | employment ended (Mia Chen, Lumen Labs) | missed | time phrase without a preposition: "left ... last month" |
| h2-2 | reporting (Lena Fischer, Raj Patel) | missed | phrasing: possessive "X's manager is Y" |
| h3-1 | employment (Kim, Vector, since 2022) | missed | phrasing: "has worked at ... since" |
| h3-3 | reporting (Kim, Noah) | missed | phrasing: "Noah manages Kim" |
| h3-4 | statement (Kim mentors two interns) | missed | pronoun "She": no coreference (by design) |

Development miss: d3-4 "He used to work at Initech" (pronoun).

Reading: the rule extractor is precise and its dates are right when it fires, but it only covers the
phrasings it was written for: recall halves on unseen wording. That is the expected weakness of a
pattern baseline and the reason for an LLM extractor. Generalising the rules would require looking at
held-out failures, so it was not done.

## Claude extractor
Not yet run: no Anthropic credentials are available on this machine, so $0 of the $10 budget has been
spent. The extractor, budget enforcement and output handling are tested with a simulated client.
To run it (estimated cost for both sets: about $0.50 to $1.50; the ledger refuses anything beyond the limit):

```bash
uv sync --extra claude
export ANTHROPIC_API_KEY=...        # or install the `ant` CLI and run `ant auth login`
uv run python -I -m gupi.evaluation --set dev --extractor claude --max-usd 2
uv run python -I -m gupi.evaluation --set heldout --extractor claude --max-usd 2   # once, after dev
```
