# Stage 3B: first real-model extraction run (exploratory)

**What this is:** one Claude extraction run over the frozen Stage 3A corpus, scored by the frozen scorer, with
candidates run through GUPI's existing validation and formation in TypeDB 3.14.1. It is **not** an independent or
blind benchmark (see Limitations). Date: 2026-11-04. Spending: $0 beyond the owner's existing Claude subscription.

**This page holds aggregate figures only.** The gold, the per-passage scoring, the raw responses and the
transcripts stay in the private folder (isolation.md).

## Run configuration
| Item | Value |
|---|---|
| Model | `claude-opus-5-5`, effort medium |
| Where | a fresh Claude Code desktop session, working folder the extraction bundle (commit `d644cc1`) |
| Permissions | default mode; the bundle's `.claude/settings.json`; each response write approved once by the owner |
| Prompt | the frozen Stage 3B prompt verbatim, plus one background sentence the app requires ("Everything needed for this task is in the files of this folder. There is no other context, and no other folder is relevant.") |
| Inputs | passages, instructions (`gupi.stage3-extraction/1`), response format (`gupi.model-response/1.1`): hashes match manifests/stage-3a.json before and after the run |
| Scorer, gold | `phase7b-stage3-scorer/1` (code hashes match the manifest); gold v1 (`dc5a9ac5…`), unchanged |
| Duration | about 4 minutes, one turn, no retries |

**Attempt 1 (aborted, not scored):** an earlier desktop session wrote no file; its seven write requests were
rejected at the permission prompt. Its transcript is preserved privately. Attempt 2 is therefore a second attempt
on this corpus (integrity risk 8). Attempt 1's drafts were never read or scored.

## Raw output and audit
- **Responses:** 32/32 files, none missing or unexpected; 32/32 valid `gupi.model-response/1.1`; 0 invalid
  outputs; 30/30 candidates grounded in their passage.
- **The frozen transcript audit: invalid,** for two reasons that come from the desktop app, not the extraction:
  1. the desktop transcript records each tool call twice under the same id, which the audit reads as every
     response being written twice;
  2. the app's own turn tools (task list ×3, wrap-up ×1) are not on the audit's allowed list.
- **Supplementary check (the audit itself was not changed):** counted by tool-call id, the session made 4 Reads (the
  four bundle files), 32 Writes (one per response, each identical to the file on disk) and the 4 app turn calls.
  No path outside the bundle was touched, and no gold id or annotation-note text appears in the transcript.
- **So the run is qualified, not validated:** isolation rests on the desktop session's permissions and this
  supplementary check, which is weaker than the original design.

## Results (k/n, 95% Wilson interval)
| Metric | Claude (`model:candidate-v1.1`) | `rules:v2.1` baseline |
|---|---|---|
| precision | 21/30 (0.70, 0.52–0.83) | 3/3 |
| recall | 21/39 (0.54, 0.39–0.68) | 3/39 (0.08) |
| F1 | 0.61 | 0.14 |
| exact / partial / overlap-unmatched / unsupported candidates | 21 / 7 / 1 / 1 | 3 / 0 / 0 / 0 |
| abstentions (appropriate) | 9 (5) | – |
| severe errors (Stage 3 definitions) | 5, of which 3 formed | 0 |

The ceiling for a faithful extractor is about 35/39 recall (four assertions are designed to be abstained from).

**Evidence integrity** (denominators are exact matches unless stated):
| Metric | Claude |
|---|---|
| claimant | 20/21 |
| claimant kind | 3/6 (the misses are `unknown` given for a named claimant; never the wrong kind) |
| direct vs reported | 20/21 |
| forwarding origin | 2/2 |
| independent corroboration (copies withheld, nothing else withheld as a copy) | 21/21 |
| temporal (every time field) | 12/12 |
| correction detected (gold corrections with an exact match) | 1/2 |
| correction kind; target (of detected) | 1/1; 1/1 |
| uncertainty preserved (hedged gold never made certain) | 2/2 |
| commitment | 19/21 |

**Pipeline outcomes** (kept separate):
- **Extractor outcomes:** 18 problems reported (9 ambiguous reference, 6 insufficient evidence, 2 inferred, 1 no
  relevant assertion). 5 flags (2 allegation, 2 commitment downgraded, 1 unreadable time).
- **Validator rejections:** extractor 0, store 0. No formation failures.
- **Formation of the 30 candidates:** 17 formed, 4 review, 9 withheld, 0 rejected.
  - Formed: 15 exact matches, 2 partial matches.
  - Admission agrees with gold on 19/21 exact matches.
- **Copies formed as new claims:** 0. **Supersessions during the run:** 0.

## What the severe errors are (pending adjudication)
| Kind | n | Formed | Nature |
|---|---|---|---|
| unsupported claim | 1 | no (withheld) | a question extracted as an employment, with `modality: question`; formation withheld it |
| invented entity | 1 | no (review) | an object name shortened from the text, and a predicate split that changes the meaning; routed to review as probable |
| invented claimant | 1 | yes | an appositive description inside a reported clause attributed to the reporter; whether gold or extractor is right needs adjudication |
| unsupported definitive assertion | 2 | yes | the statement's content matches, but the predicate is split into verb plus object text, so the exact-predicate rule leaves it a partial match |

## Limitations
- **Claude-authored:** the 32 passages and the 39 gold assertions were written by Claude (the Stage 3A session),
  and the extractor is the same model family. **No person has checked the gold.**
- **No independent adjudication yet:** 8 partial or overlapping matches and 4 disputed misses are listed
  privately for an adjudicator who is not the developer. All figures above are before adjudication.
- **Small:** 32 passages, 39 assertions; correlated within passages; wide intervals.
- **Weaker isolation:** a desktop session with permission prompts, not the strict design; the frozen audit could not
  accommodate the desktop transcript format, and a supplementary check stands in for it.
- **Second attempt:** the aborted first attempt is documented and preserved.
- **Not an integration test:** the run used a person approving each file write in an interactive session. It does
  not demonstrate automated model integration, and it cannot establish superiority over any other system.
