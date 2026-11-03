# Phase 5 proposal: memory evaluation (LoCoMo, LongMemEval)

Goal (gate, from the brief): integrate LoCoMo and LongMemEval using official, permitted datasets and their
documented protocols; record model versions, prompts, tokens, latency, cost and splits; compare equivalent
configurations against text and other practical baselines; no leakage or tuning on held-out data; fully
reproducible reports, an error taxonomy, and at least one controlled ablation of structured versus
text-only retrieval.

## What is possible offline, and what is not
Both benchmarks are natural, multi-session conversations with free-text questions and answers. GUPI's
offline rule extractor was written for a handful of phrasings and will recover little from them, and
both benchmarks' official metrics score generated answers, normally with an LLM judge. So:
- **Offline (no credentials):** dataset adapters, ingestion of sessions as dated observations, and the
  *retrieval* part of the protocol where the datasets mark evidence turns: does keyword retrieval (and
  structured retrieval over rule-extracted claims) surface the evidence within the top k, as of the
  question date? This gives a controlled structured-versus-text ablation on retrieval, honestly labelled as
  not an end-to-end score.
- **Needs an LLM:** extraction good enough for these conversations, answer generation and the official
  judged metrics. That is the ClaudeExtractor (Phase 2) plus a question-to-structure step, run through
  the budget ledger.

## Proposed steps
1. Verify each dataset's current licence, terms and official split/metric definitions from the original
   sources; record them in docs. No download until the owner approves the specific files (name, source,
   size).
2. Adapters: dataset sessions -> observations with their own dates, in disposable databases; a small
   fixed development slice and the remaining questions untouched as held out.
3. Offline retrieval evaluation: evidence recall@k and abstention cues for keyword vs structured (rule
   extraction), per question category (temporal, multi-hop, knowledge update, abstention).
4. Scale fixes found by real data (batched ingestion; ingestion is about 100 claims per second today).
5. With approval and credentials: Claude extraction on the development slice first, with per-question token
   and cost logging, then the held-out run once, judged per the official protocol; never mixed with vendor-
   reported figures.

## Decisions needed from the owner
- **Licences and downloads:** approve fetching the datasets after the licence check.
- **LLM budget:** the remaining $10 covers small slices only (e.g. a few dozen LongMemEval questions with
  extraction and answering). A full run needs a larger, explicit budget, or Phase 5 stays offline and
  retrieval-only.
- **Embeddings:** most published memory systems use them; a fair text baseline may need one. Still deferred,
  or choose a local model (a large dependency) now?
