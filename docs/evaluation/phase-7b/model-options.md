# Model options: Claude and local models (nothing called, downloaded or installed)

## Prices (verified)
These were fetched from Anthropic's published pricing page
(`platform.claude.com/docs/en/about-claude/pricing`) on 2026-11-04. They match the ledger's
`PRICES_USD_PER_MTOK` (recorded on 2026-10-06), except that the ledger charges Haiku 5.5 at its >100K-token
rate, deliberately.

| Model | Input $/MTok | Output $/MTok | Cache read | Batch (50% off) | Notes |
|---|---|---|---|---|---|
| Claude Opus 5.5 (`claude-opus-5-5`) | 4 | 20 | 0.20 | 2 / 10 | thinking cannot be disabled (effort is the only control) |
| Claude Sonnet 5.5 (`claude-sonnet-5-5`) | 2 | 10 | 0.10 | 1 / 5 | thinking can be turned off (`{type: "between_tools"}` at effort high or below) |
| Claude Haiku 5.5 (`claude-haiku-5-5`), prompt ≤ 100K | 0.10 | 0.50 | 0.01 | — | its tokenizer counts the same text as about 30% more tokens; no server-side fallback |

**Recheck these before Stage 2,** then update the ledger table deliberately if they differ.

## The existing Claude extractor (`gupi/extraction/claude.py`)
**What it already does:**
- **The request:** a Messages API call with `output_config.format` JSON schema, effort medium, and
  `fallbacks: "default"`.
- **The ledger:** reserves the worst case and settles the actual cost (fail closed, $10 lifetime).
- **Failures:** a refusal, a truncation or unparseable output produces no claims.

**What it lacks for this experiment:**
- **The wrong output format:** it emits the **Phase 2 extraction contract** (mentions, plus claims with
  start, end and ongoing), not `gupi.candidate/1`. It has no polarity, modality, commitment, attribution, time
  kinds or relations.

**Work required (Stage 2, after approval):**
1. **Prompt and schema:** a new prompt version (`p2`) and output schema, as in model-extractor-design.md.
2. **Grounding:** a grounding and normalisation step that builds `CandidateSet`s.
3. **Recording:** a recorder, which stores each request and response locally (git-ignored, never committed)
   so that scoring and tests can replay them offline.
4. **Model choice and caching:** model selection (Sonnet or Haiku); thinking off or low effort; prompt
   caching of the fixed system prompt and schema.
5. **Tests:** against recorded and synthetic responses only. No live call in tests.

**Prompt requirements:**
- **Field definitions:** each enum, with a one-line definition and one developer example. The examples are
  not from S1 or S2.
- **Exact copying:** "copy text exactly; never paraphrase; never supply dates or offsets".
- **Uncertainty:** explicit instructions to prefer `unknown`, `possible` or `insufficient-evidence` over a
  guess.
- **Every field required.**
- **Versioning:** the prompt text and schema are hashed into the extractor's method string.

**Validation and retries:**
- **Schema errors:** a response that fails the JSON schema, or grounding, is **not retried** in a scored run.
  It is recorded as `invalid-model-output` or `grounding-failure`, so the scored run measures first
  answers.
- **Transport errors:** errors with no billed response are retried at most twice, with backoff.
- **Refusals and `max_tokens`:** recorded as outcomes.

**Configuration and secrets:**
- **The optional extra:** `uv sync --extra claude` (it is not in the default installation, and stays out).
- **The key:** `ANTHROPIC_API_KEY` in the environment only, never in files or logs. It must belong to an API
  account with credits; a Claude Max subscription does not provide them.
- **Spending:** the ledger's lifetime limit ($10) and a per-run cap (`run_cap_usd`).

**Reproducibility limits:**
- **Sampling:** responses are not deterministic (and sampling parameters are not available on these models).
- **Model changes:** model snapshots can change behind an alias. Server-side fallbacks may route to another
  model, and the ledger records which one billed.
- **How to reproduce:** from the recorded responses. Re-running live is a new run.

## Token and cost estimates (*estimates*; measured values come from the ledger in Stage 2)
**Assumptions:**
- **Prompt:** a fixed system prompt plus schema of about 2,100 tokens, cacheable.
- **Passage:** S1 about 200 tokens, S2 with context about 250.
- **Output:** about 500 tokens of JSON per passage (about 2–3 assertions).
- **Thinking:** off (Sonnet, Haiku) or about 1,500 tokens (Opus at low effort).

| Model | Per passage | 80 scored passages (S1 + S2) | + 20 DEV passages, prompt development ×3 | Total |
|---|---|---|---|---|
| Sonnet 5.5, thinking off | about $0.010 (≈ $0.006 with a cached prompt) | about $0.80 | about $0.60 | **about $1.40** |
| Haiku 5.5, thinking off (about 30% more tokens) | about $0.0006 | about $0.05 | about $0.04 | **about $0.09** |
| Opus 5.5, effort low | about $0.05 | about $4.00 | about $3.00 | about $7 (over budget with the others) |

**Latency** (*estimate*):
- **Sonnet:** about 5–12 s per passage synchronously, for about 500 output tokens.
- **Haiku:** about 2–5 s.
- **Opus with thinking:** about 15–40 s.
- **Batch:** it halves cost but makes latency meaningless, so batch is not used for latency figures.

**Recommendation:** Sonnet 5.5 as Candidate B, with Haiku 5.5 as a second, cheaper arm on the same frozen
corpus. Proposed Stage 2 cap: **$3**, with a per-run cap of $1.50. Opus 5.5 is excluded: it costs about 5×
as much, and its thinking cannot be disabled.

## Local models (Option C; evaluate only if justified)
**Hardware:** Apple M2 Pro, 16 GB of unified memory, 178 GB of disk free. No inference runtime is installed.

| Class | Memory at 4-bit | Download | Expected limits |
|---|---|---|---|
| 7–9B instruct (e.g. Qwen, Llama, Mistral families) | about 5–6 GB in use, plus context | 4–6 GB | weaker at modality, commitment and attribution; needs grammar-constrained JSON; about 10–20 s per passage (*estimate*) |
| 3–4B instruct | about 3 GB | 2–3 GB | faster, and markedly weaker at nuanced fields |
| 14B+ | about 9–10 GB | 8–10 GB | crowds out TypeDB (Docker is allotted 7.7 GB) on 16 GB |

**What this option needs:**
- **A runtime:** llama.cpp (MIT, Metal) or MLX, both new infrastructure.
- **A model licence check** (permissive for Qwen, Mistral and Phi; community or use terms for Llama and
  Gemma).
- **Approval** for the download.

**Assessment:** not recommended for the first experiment.
- **No reason to expect it to compete:** there is no evidence that a 16 GB-class model would match Sonnet on
  attribution and certainty, which is what this experiment is mainly about.
- **Its costs:** it adds an install and a download, and a second prompt-tuning effort.
- **When to reconsider:** only if Candidate B succeeds and a $0 recurring cost then matters.
