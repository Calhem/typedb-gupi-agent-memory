# Extraction efficiency: a design investigation

**Nothing here has been run on a model, and no infrastructure was added.** Rates are from the manual pass on 788 development
turns. Costs are rough, from `phase8c_salience.scale_table`, for `gpt-4o-mini` at AML's stated 300 million tokens, assuming
LoCoMo-sized turns. They replace the figures in the run plan, which assumed far more output than chat produces.

## What the manual pass shows
**72% of turns have nothing to extract.** That's the opportunity.

| A free text filter (a statement about the speaker, with something factual in it) | |
|---|---:|
| Turns kept | 27% |
| Turns with a claim that it keeps | 69% |
| Turns linking two things that it keeps (only 5 exist) | 60% |
| Gold turns it keeps | 63% |

So it would cut calls by almost four times and lose about a third of the claim turns. Whether that's acceptable depends on
whether those claims are valuable, which isn't yet shown. The filter was written after seeing development data.

## Cost at scale
| Design | Requests | Rough cost |
|---|---:|---:|
| Every turn, one per request (built) | 7.9M | $2,700 |
| Every turn, 5 per request | 1.6M | $750 |
| **Every turn, 20 per request** | **395K** | **$415** |
| Text filter, one per request | 2.1M | $820 |
| **Text filter, 20 per request** | **105K** | **$205** |

Request-level overhead is the main cost, because the instructions are about 1,900 tokens every time, so **batching saves
more than filtering.** The two combine. OpenAI's half-price batch service doesn't apply, because AML's Add must finish
synchronously. Prompt caching would lower these further.

## How a batch keeps attribution
No new infrastructure, and the parser is unchanged:
1. **Window:** AML's Add already splits at 20 messages, so use that. Each turn gets a number.
2. **Reply:** one entry per turn number, each in today's format.
3. **Parsing:** each entry goes through `model:candidate-v1.1` against **its own turn only.** A quote from the wrong turn fails
   grounding, so a mix-up costs coverage and can't misattribute evidence.
4. **Replay:** the recording key covers the whole window, so a changed batch misses, as now.
5. **Failure:** a truncated reply loses a whole window, not a turn. Each lost turn stays reported, so it isn't silently empty.

**Open risk:** extraction quality across a window is unmeasured. The two context turns aren't needed, since neighbours are
in the window. Pronouns remain unresolved by design.

**Recommendation:** when extraction is next funded, test 20-per-request first, with the filter as a separate comparison.
**But cost isn't the deciding question.** See [findings.md](findings.md): first establish that claims earn their cost.
