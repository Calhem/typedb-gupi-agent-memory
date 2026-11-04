# Phase 7A: next extractor options

**Nothing here was run:**
- no model was downloaded
- no runtime was installed
- no API call was made

Figures marked *estimate* are reasoned, not measured. The environment is an Apple M2 Pro with 10 CPU cores
and 16 GB of unified memory, of which 178 GB of disk is free. Python 3.13 runs via uv, with onnxruntime
1.31.1 (used by fastembed) and anthropic 2.4.0 installed. There is no local LLM runtime: no Ollama,
llama.cpp or MLX.

## Option A: expanded deterministic rules
| Aspect | Assessment |
|---|---|
| Expected improvement in the domain | **Large on organisational prose, near zero on these datasets.** The Phase 2 held-out misses suggest about 5/12 → 10/12 (an upper bound; seen messages). On the conversation sample: 0 → 1 of 39 assertions without a contract change |
| Missing patterns | About 25–35, from the probes and samples. Verbs: began, took a job, quit, resigned, appointed, employed, let go, has left. Structures: leading "In <date>,", lead-ins, trailing clauses, apposition, "is the X at", possessives, inverse "manages", "boss". Agreement: "I report", "I work". Names: lowercase, 3+ words, "&". Dates: ISO, "N months ago". Several interact: lead-ins and trailing clauses need `search` instead of `fullmatch`, which changes the false-positive profile |
| Maintenance | High, growing with each phrasing; patterns already interact (clause splitting, cue prefixes). Every addition needs a probe and a frozen-set rerun |
| False-positive risk | Rises sharply with looser matching. D1 shows what happens even now: "She" became a person. Embedded matches ("I heard from Sam that X works at Y and loves it") need attribution handling to avoid stripping the reporter |
| Temporal and attribution fidelity | Excellent where it matches: kinds (start, end, held since, holds at), hedges, reported speech and corrections are explicit and deterministic |
| Cross-turn context | Not reasonably: pronoun and ellipsis resolution, and "there" or "them", need discourse state that pattern rules handle poorly. Fixing D1 means *refusing* pronouns, not resolving them |
| Unnamed employers ("lost my job") | Not a rules problem: it needs a contract decision (placeholder referents or a new claim shape) |

**Verdict:** worth doing for D1, D2 and the cheap, high-precision gaps (`rules:v2.1`). It cannot address the
domain gap, which is the main cause on conversational data.

## Option B: local model extraction
**Candidates to verify before any download.** This is from knowledge up to mid-2026; check versions and
licences then:

| Class | Examples | Size at 4-bit | Licence |
|---|---|---|---|
| 7–9B instruct | Qwen 2.5/3 7–8B, Llama 3.1 8B, Mistral 7B | ~4–6 GB | Apache-2.0 (Qwen, Mistral); Llama community licence (attribution, acceptable-use policy) |
| 3–4B instruct | Phi-3.5/4-mini, Qwen 3–4B, Gemma 3 4B | ~2–3 GB | MIT (Phi); Gemma terms |

| Aspect | Assessment |
|---|---|
| Hardware | 16 GB unified memory runs a 7–8B model at 4-bit comfortably, but not alongside large TypeDB loads; a 3–4B model leaves headroom |
| Compatibility | Needs a runtime: llama.cpp (MIT, Metal) or MLX. **Both are new infrastructure and need approval.** onnxruntime alone is not a practical LLM path |
| Structured JSON | llama.cpp supports grammar- or JSON-schema-constrained decoding, which guarantees well-formed output in the candidate shape. It does not guarantee correct content |
| Throughput | *Estimate:* 7–8B Q4 on M2 Pro is roughly 20–35 tokens/s generation, a few hundred tokens/s prompt. At about 300 output tokens that is 10–20 s per passage: about 20–35 minutes for 100 passages, impractical for 250,000 turns (weeks). A 3–4B model is about 2× faster |
| Implementation effort | Moderate: a `CandidateExtractor` that prompts for `gupi.candidate/1`, then computes spans locally by exact substring search, never trusting model offsets; plus a runner, a probe run, the frozen-set scorer. About 1–2 days, plus the download |
| Spans, modality, attribution, time | Spans: enforceable by local exact-match validation (`validate` already rejects quotes not in the passage). Modality, commitment and attribution: plausible but unmeasured for small models, a known weak point. Time: the model should copy phrases and `gupi.timeexpr` should read them, as now |
| Licensing and deployment | Weights must be downloaded (4–6 GB) and are not redistributable here. Llama and Gemma carry use terms; Qwen, Mistral and Phi are permissive |

## Option C: Claude-backed extraction (existing `gupi.extraction.claude`)
| Aspect | Assessment |
|---|---|
| Usable with the current candidate representation? | **Not directly.** `ClaudeExtractor` emits the Phase 2 extraction contract (mentions and claims with start, end, ongoing, basis, confidence), validated by `gupi.extraction.contract`. It has none of `gupi.candidate/1`'s polarity, modality, commitment, attribution (asserted-by, mode, transmission), time kinds (holds-since, holds-at) or relations. Using it with the store needs a new prompt version and output schema for `gupi.candidate/1`, or a converter, which would have to invent defaults (not acceptable) |
| API configuration | `uv sync --extra claude` (anthropic 2.4.0 is already installed); `ANTHROPIC_API_KEY` for an API account with credits. **A Claude Max subscription does not provide API credits**; none are configured on this machine. Model `claude-opus-5-5`, effort medium, structured output, `fallbacks: "default"`; every call is reserved and settled in the fail-closed $10 ledger |
| Tokens for a small experiment | *Estimate* per passage: input about 1,000–1,600 (system prompt about 430, output schema about 400, schema description about 300, passage 100–600); output about 300–400 JSON tokens plus adaptive thinking, which cannot be disabled on Opus 5.5, of about 300–2,000. Total about 0.7–2.4k output |
| Cost for 50–100 passages | *Estimate,* at the ledger's recorded prices (2026-10-06): Opus 5.5 ($4/$20 per MTok) about $0.02–0.05 per passage, so **$1–5 for 50–100**. Sonnet 5.5 ($2/$10) about $0.5–2.5. Haiku 5.5 ($0.50/$2.50) about $0.15–0.65. The ledger reserves a worst case of about $0.8 per call (8,000 output tokens at the highest fallback price) and settles to the actual cost |
| Structured-output validation | The JSON schema guarantees shape. Content is checked locally: exact quotes and mention text, schema roles, time phrases read by `timeexpr` (the model never writes dates); a refusal or truncation yields nothing |
| Risks | Invented entities (pronoun "resolution" to a wrong person); invented or normalised dates; paraphrased quotes; relationships inferred from presupposition; over-extraction of opinions as facts |
| Keeping interpretation apart from evidence | Already in the design: the candidate's passage is the exact source span; the model's reading is a hypothesis (`method` names the model and prompt version); `basis: inferred` and any non-certain commitment go to review under formation:v1; nothing is accepted without the policy, and the store keeps the payload for audit |

## Comparison
| | A rules | B local model | C Claude |
|---|---|---|---|
| domain gap on conversations | no | yes (prompted ontology) | yes |
| phrasing gap in the domain | partly | likely | likely |
| cross-turn context | no | limited (short window) | yes (window in the prompt) |
| fidelity of spans, time, attribution | high where it matches | unknown; validator-enforced spans | unknown; validator-enforced spans |
| cost | developer time | 4–6 GB download, a runtime, ~10–20 s/passage | ~$1–5 per 100 passages, within the ledger |
| needs approval | no (but a version bump) | download and runtime | API key and spending |
| new code | rules:v2.1 | candidate/1 extractor + runtime adapter | candidate/1 prompt version + schema |
