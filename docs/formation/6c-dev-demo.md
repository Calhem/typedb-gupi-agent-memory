# Phase 6C development demonstration (not a benchmark)

Date: 2026-11-03. Test: `tests/integration/test_formation_dev_demo.py`, against TypeDB 3.14.1.

**What it does.** It runs the three Phase 2 **development** conversations (12 messages) end to end:
1. ingest each message
2. extract it with `rules:v2`
3. form its candidates with the `formation:v1` policy
4. ask questions under answer semantics v2

**This is not an independent evaluation.** The development split shaped `rules:v1`, on which `rules:v2`
builds. It shows only that formed claims can be queried, and that what waits for review does not change
memory. No frozen dataset was changed.

## Decisions
| Outcome | Count | Which |
|---|---|---|
| formed | 7 | d1-2, d1-3, d1-4, d2-1, d2-2, d3-1, d3-3 |
| review | 1 | d2-3 "Correction: Marco Rossi stopped reporting to Elena Petrova in April 2025." |
| withheld | 0 | |
| rejected | 0 | |

4 messages produced no candidate:
- **two the extractor reported** as domain sentences it cannot parse:
  - d1-1, because of the "Quick intro:" prefix
  - d3-4, "He used to work at ..."
- **two it passed over silently:**
  - d2-4, "is a Staff Engineer at", a known missing pattern
  - d3-2, outside the domain

## Questions (v2)
| Question | Answer | Why |
|---|---|---|
| Tom Okafor at Northwind on 1 July 2025 | FALSE | "left Northwind in May 2025": a continuing termination |
| Priya Shah reports to Dana Li when said (10 June 2025, 11:02) | TRUE | "Since June 2025, Priya Shah reports to Dana Li" holds when said |
| the same on 15 May 2025 | UNKNOWN | "since June" is a lower bound: never FALSE before it |
| Marco Rossi reports to Elena Petrova on 1 June 2024 | TRUE | "since 2023": certainly held from 1 January 2024 to the statement |
| the same on 1 June 2025 | UNKNOWN | the correction that would decide it is awaiting review, so it is not in memory |
| Alice reports to Sam on 1 October 2025, 09:02 | TRUE | "Alice now reports to Sam" |
| Tom Okafor at Northwind on 1 July 2025, as believed on 1 June 2025 | NOT_YET_KNOWN | the departure was recorded on 10 June |

## Defects the demonstration found (fixed, with regression tests)
1. **A correction slipped through review.** A correction whose target the extractor could not name was formed
   automatically (`254da05`). Now any passage that opens with a correction cue goes to review.
2. **A "since" bound fell after its own statement.** "Since June 2025, ...", said on 10 June, was mapped as
   certainly holding only from 1 July, which is after it was said (`3367070`). The lower bound is now capped
   at the statement's own instant.
