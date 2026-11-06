# Phase 8C: capped experimental run plan

**Status: awaiting the owner's approval. No paid call has been made.** Prices and AML's model rule were re-checked on
2026-11-06. Estimated tokens are characters divided by 4, computed from the real requests by
`uv run python -I -m gupi.benchmarks.phase8c plan`. Real usage will differ; the caps do not depend on the estimate.

**In plain English:** we would pay OpenAI to read each chat message and propose facts. GUPI's existing checks then decide
what is kept. Each stage is small, stops by itself, and must pass before the next one is even asked for.

## Price and model
| Item | Value | Source |
|---|---|---|
| Model | `gpt-4o-mini`, required for LLM components in AML's open-source division | agentmemoryleaderboard.ai |
| Standard price | $0.15 per million input tokens, $0.60 per million output | developers.openai.com/api/docs/pricing |
| Cached input | $0.075. The ledger ignores this, so it never under-counts | same |
| Spending limit | the existing $10 total ledger; nothing has been recorded in it on this machine | `gupi.budget` |

## Gates
Each gate is a separate approval.
| Gate | Data | Calls | Typical | High | Cap | Purpose |
|---|---|---|---:|---:|---:|---|
| 1a smoke | first 40 turns of `conv-26` (development) | 40 | $0.02 | $0.03 | **$0.10** | does it work at all? |
| 1b pilot | all of `conv-26`, `conv-30` (development) | 788 | $0.35 | $0.52 | **$1.00** | coverage, admission, connectivity |
| 2 frozen | `conv-41`, `conv-42` (held-out, once) | 1,292 | $0.57 | $0.85 | **$1.50** | the actual test |
| 3 answers | 135 questions, 5 systems, plus judging | 1,350 | $0.54 | not bounded yet | set later | answer accuracy |

**Approval requested now: Gate 1 only, a $1.00 cap covering 1a and 1b together.** The owner needs to set
`OPENAI_API_KEY` in the environment; a key is never written to a file or a log.

## Stop conditions
**Automatic, during a run (frozen in `benchmarks/phase8c.json`):**
- The ledger would pass the approved cap: the call is refused before it is sent.
- More failed replies than 5% after 20 calls, or 3 in a row.
- The gate's call count is reached.
- Whatever was paid for stays recorded, so a stopped run loses nothing.

**At the end of each gate, before asking for the next:**
| Check | Rule | If it fails |
|---|---|---|
| Unusable assertions (grounding, ambiguous span, invalid, validation) | at most 30% | stop; report |
| Claims formed | more than zero | stop; report |
| Claims linking two referents | at least 10% | stop: there is no graph to traverse, and Gate 2 is not requested |
| Severe integrity findings | zero | stop; fix first |
| A person reads a sample of formed claims | no systematic false memories | stop; report |

**A changed prompt is a new version.** Recording keys include the prompt, so a change misses every recording and is paid
for again. At most one prompt revision is planned, after Gate 1, and never after Gate 2 starts.

## Risks the pilot exists to measure
All of these come from reading the code. None is a measured result.
| Risk | Why | What would show it |
|---|---|---|
| **Few links** | a claim only makes a graph edge with two referents; "I went to a support group" has one | `linking_share` |
| **One-time events withheld** | "I ran a race last week" reads as a dated event, and formation withholds it (known since Phase 8A) | `withheld_for_time` |
| **"I" stops assertions** | the parser finds "I" by substring, so "I" inside "It" or "Italy" can make a span ambiguous. 20% of development sentences containing "I" (107 of 527) could hit this if quoted whole | `ambiguous-span` |
| **"my sister" stops assertions** | vague references are never resolved, by design | `ambiguous-reference` |
| **gpt-4o-mini's quality on this contract is unknown** | Stage 3 used Claude, and on business text, not casual chat | everything above |

## Cost at leaderboard scale
Rough only: AML states about 300 million tokens of textual data, and this assumes LoCoMo's average turn.
| Approach | Rough extraction cost |
|---|---|
| One request per message (built) | about **$3,500** |
| One request per 20 messages (not built) | about **$1,350** |

**Per-message extraction is not viable for a full AML run as it stands.** Filtering messages or batching would be
needed. Both change extraction quality, so neither is assumed. This matters to evaluation criterion 5.
