# R2: bare retractions

**Failure class (Stage 3B, X3-17):** a message that retracts an earlier statement without restating it ("ignore
what I said yesterday about …"). Format 1.1 attaches a correction only to an assertion, so the model reported a
problem, produced no candidate, and the retracted claim stayed formed with nothing for a reviewer to see.

**The fix:** in the offline model interface (`model:candidate-v1.1`), code reads the message itself for a
retraction phrase, whatever the model returned. For each sentence that has one and that no assertion already
carries, it emits **one candidate for what the author asserts, the retraction**:

| Field | Value |
|---|---|
| type | generic `statement` (provisional, as every statement is) |
| subject | the author, `I`, located in the sentence |
| predicate-text / object-text | the retraction phrase / what it is about, up to the first comma, as written |
| relation | `retracts`, `marked: stated`, **target null** (format 1.1, D3) |
| flags | `bare-retraction`; `retraction-possible-targets`: earlier candidates in the thread naming a word of what it is about, listed only |

Formation already sends a null-target retraction to review ("a stated correction whose target is not
established"), and the store records a correction suggestion whose resolution is `missing` or `ambiguous`.
**Nothing is superseded:** approving the retraction forms the retraction statement only; the earlier claim stays
believed until a reviewer records a supersession (`store.assign_correction_target`, `Memory.supersede`).

**Never silently dropped:** a retraction with no known author, or with no first person to attach it to, gives
the explicit outcome `bare-retraction-unrecorded` in the extraction report.

**A broken model response cannot hide one:** the message is read by code, so a response that fails to parse
still yields the review item, and nothing else.

**Phrases read:** ignore / disregard / forget what I said (wrote, told you, mentioned) or my last (earlier,
previous) message; I retract / withdraw that; I take that (it) back; scratch that; I was wrong about; I mixed
him (her, them) up. Not after "don't", "do not", "never", "didn't".

## Before and after (synthetic, `tests/unit/test_stage4_r2_retractions.py`, `tests/integration/test_stage4_integrity.py`)
| Case | Before | After |
|---|---|---|
| "please disregard what I wrote this morning about Tomas" (model: nothing, or a problem) | no candidate; retracted claim formed, unflagged | one candidate → **review**, target null, possible target listed; retracted claim still believed |
| two retraction phrases in one sentence | – | one candidate |
| "Don't forget what I said about the deadline" | nothing | nothing |
| retraction with no author | nothing, silently | outcome `bare-retraction-unrecorded` |
| a retraction the model already carried on an assertion | null-target or resolved correction | unchanged, no duplicate |
| reviewer approves the retraction | – | the retraction is formed; the earlier claim is still believed |

## Compatibility
No format change. Existing responses parse as before; a message containing a retraction phrase now yields one
more candidate. Candidate format 1.1 already allowed a null-target `retracts`.

## Limits
- **Lexical:** a retraction worded outside the listed phrases is still missed ("that's not right, sorry").
- **The answering layer does not yet mark claims as "retraction pending"**: the pending item is visible in the
  candidate store's review queue, not in answers.
- **Only the model interface reads retractions;** `rules:v2` is unchanged.
