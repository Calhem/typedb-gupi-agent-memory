# External benchmark datasets

Datasets are **not** in this repository. They are downloaded to `.data/` (git-ignored) and verified against
the checksums below. Only ids, aggregate scores and checksums are committed.

| Dataset | Source and version | File | SHA-256 | Licence |
|---|---|---|---|---|
| LoCoMo | github.com/snap-research/locomo, commit `cbfbc1dba6bc53d00625212a0f22d55ffee7c1fc` (git blob `d95b8724…`) | `data/locomo10.json` (2,805,274 bytes) | `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4` | CC BY-NC 4.0 |
| LongMemEval (cleaned, 2025-09) | huggingface.co/datasets/xiaowu0162/longmemeval-cleaned, revision `98d7416c24c778c2fee6e6f3006e7a073259d48f` | `longmemeval_s_cleaned.json` (277,383,467 bytes) | `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442` | MIT |
| LongMemEval (cleaned, 2025-09) | same revision | `longmemeval_oracle.json` (15,388,478 bytes) | `821a2034d219ab45846873dd14c14f12cfe7776e73527a483f9dac095d38620c` | MIT |

Checked 2026-11-03. LongMemEval's checksums match the Hugging Face LFS hashes; LoCoMo's file matches the
GitHub blob hash. `longmemeval_m_cleaned.json` (2.7 GB) was not downloaded.

**Licence conditions** (see also docs/known-issues.md: LoCoMo's non-commercial terms are an unresolved
compliance consideration). LoCoMo is CC BY-NC 4.0: non-commercial research use with attribution (Maharana
et al., 2024, "Evaluating Very Long-Term Conversational Memory of LLM Agents"); its content must not be
redistributed here. GUPI uses it as an open-source research experiment; any commercial use needs a separate
review. LongMemEval is MIT (Wu et al., 2024, "LongMemEval: Benchmarking Chat Assistants on Long-Term
Interactive Memory").

**Structure used.**
- LoCoMo: 10 conversations (5,882 turns, 19-35 dated sessions each), 1,986 questions with evidence turn ids
  (`D<session>:<turn>`). Categories (from the official evaluation code and question wording): 1 multi-hop,
  2 temporal, 3 open-domain, 4 single-hop, 5 adversarial (unanswerable; tests abstention).
- LongMemEval S: 500 questions, each with its own history of about 50 dated sessions (~490 turns); answer
  sessions are given and answer turns marked (`has_answer`). Types: single-session (user, assistant,
  preference), multi-session, temporal reasoning, knowledge update; 30 abstention questions (`_abs`).

**Splits.** Neither dataset defines a development split, and their own files are used unchanged.
`benchmarks/split.json` fixes ours: LoCoMo conversations `conv-26` and `conv-30` (304 questions) are
development, the other 8 are held out; LongMemEval questions with sha256(question_id) mod 10 == 0 (53) are
development, the other 447 held out.

Download (verifies checksums): `uv run python -I scripts/fetch_datasets.py`.

## Embedding model (optional `embeddings` extra)
| Model | Source and version | File | SHA-256 | Licence |
|---|---|---|---|---|
| BAAI/bge-small-en-v1.5 (quantised ONNX, 384 dimensions, 64 MB) | huggingface.co/Qdrant/bge-small-en-v1.5-onnx-Q, revision `aa8f8b060edb00e03bfdd08813a2949946c8ba55`, via fastembed 0.9.1 | `model_optimized.onnx` | `51f1bd0addd6e859e42c2c8021a5e5461385bb676a649f4b269aa445449f2431` | MIT |

Downloaded once by fastembed into `.data/models/` (git-ignored); after that it runs offline on the CPU.
