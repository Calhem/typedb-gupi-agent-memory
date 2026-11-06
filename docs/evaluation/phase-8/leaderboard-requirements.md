# Agent Memory Leaderboard (AML): requirements check

**Checked: 2026-11-06.** Nothing here was submitted, and no adapter was built. Rules can change: re-check all of this
before Phase 8E.

**Sources (official):**
| Source | URL |
|---|---|
| Website, with Docs, API Guide, Rules and Evaluation | https://agentmemoryleaderboard.ai/ , `/docs`, `/api-guide`, `/rules`, `/evaluation` |
| Competition page | https://agentmemoryleaderboard.ai/competition/ |
| Public repository | https://github.com/AML-memory/agent-memory-leaderboard |
| Answer and judge pipeline for LoCoMo-Refined | https://github.com/AML-memory/agent-memory-leaderboard/blob/main/data/locomo-refined/pipeline.py |
| Cycle 1 archive | https://huggingface.co/spaces/agent-memory-leaderboard/leaderboard |

**How they were read:** the website refused automated fetchers (HTTP 503) but served a normal browser user agent. All
its pages are one application, so the text was read from the page source, in English and Chinese.

## Headlines for GUPI
1. **Cycle 2 has closed.** Materials closed 31 October and evaluation on 4 November 2026 (UTC+8); results are due in
   mid-November. **No later cycle is announced** on the pages checked.
2. **The evidence regime is very different from our recall@5 and @10 tests.** Search must support `top_k = 100`, and the
   answer stage gets up to 117,760 tokens. Ranking near the top matters less; **finding the evidence within 100 items
   matters more.** Phase 8B reports recall@50 as well, for that reason.
3. **Only `id`, `content`, `score` and `created_at` are read; other fields are ignored.** GUPI's qualifications
   (allegation, dispute, pending retraction) must be written **inside the `content` text**, or they vanish.
4. **The fixed answer prompt says** (LoCoMo-Refined pipeline, instruction 8): "If memories conflict, prefer the most recent
   supported memory." GUPI's refusal to resolve disputes will be resolved by the answer stage unless content says
   otherwise. Whether that helps or hurts scores is unknown.
5. **The open-source division fixes the models:** `text-embedding-v4` and `gpt-4o-mini`. So automated claim extraction
   there means `gpt-4o-mini`. Our Stage 3 results came from Claude and do not transfer.
6. **TypeDB is allowed:** "Databases, indexes, and internal architectures are unrestricted."

## Confirmed requirements
| Topic | Confirmed |
|---|---|
| **Who answers** | AML generates answers and scores them. Participants supply only Add and Search. Search must not generate final answers or disguise answers as memories |
| **Scoring** | end-to-end; judge labels each answer CORRECT or WRONG in the LoCoMo-Refined pipeline. Formal samples stay in a fixed denominator. Overall and category breakdowns are shown; scores are not comparable across tracks |
| **Tracks** | Textual (6,000+ instances, 32 data sources, about 300M tokens), Coding (300), Multimodal (nearly 5,000). Each ranked separately |
| **Divisions** | Open-source Methods; Commercial Products. Prizes are open-source only (Cycle 2: US$22,000 in total) |
| **Models** | Open-source: embeddings `text-embedding-v4`, LLM components `gpt-4o-mini`, rerankers unrestricted. Commercial: no restriction |
| **Textual competencies** | fact recall, multi-hop relations, temporal events, memory governance (updates, conflicts, deletion), personalisation, rule execution, safety and privacy, plus Streaming memory |
| **Textual data** | repository lists beam, clbench, locomo-refined, longmemeval-s, personamem, scriptmem. Formal evaluation also uses private sets |
| **Hosting** | participant-hosted, publicly reachable HTTP(S) endpoints. No repository-only or Docker-only entries. URLs must not be private, loopback or link-local. A health endpoint answers an unauthenticated GET |
| **Cost** | free to enter. Participants pay for their APIs, databases, bandwidth and compute; AML pays for Answer and Eval |
| **Open-source materials** | public repository, fixed commit, attribution of prior work, method changes |
| **Quotas (Cycle 2)** | Smoke: once an hour, at most 30 per track. Full: at most 2 per key and track; the second at least 30 days after the first |
| **Version lock** | once a Full run is accepted, the version cannot be replaced or withdrawn because of a bad result |
| **Prohibited** | hard-coding, benchmark leakage, prompt injection, live human answering, result manipulation, retrieval across `user_id`, replacing the query with an answer or gold |
| **Data handling** | evaluation data only for the task; no training or analytics; delete within 30 days |

## Add and Search contract (as published)
**Add:** `POST`, synchronous. Memory must be persisted and immediately searchable before HTTP 200.
| Field | Notes |
|---|---|
| `request_id`, `user_id`, `session_id` | required; echoed back exactly with `success: true` |
| `messages[]` | ordered; `role`, non-empty `content`, optional `timestamp` in Unix milliseconds |
| chunking | plain text is split at 20 messages or 2,000 words, whichever comes first. Maximum 30 minutes per request |

**Search:** `POST`.
| Field | Notes |
|---|---|
| `query`, `user_id`, `top_k` | required; formal `top_k` is 100. Returning more is a contract error |
| `options` | multiple-choice options, sent as text; no gold |
| Response | `{"data": [{"id", "content", "score"?, "created_at"?}]}`, ranked. Empty array when nothing is found |
| Not sent | `metadata`, `filters`, `rerank`, `keyword_search`, `app_id`, `agent_id` |

**Context budget (textual):** 128,000-token window, minus 8,192 output and 2,048 margin: 117,760 input tokens, trimmed
from the end of the ranking. Auth: Token, Bearer or X-Api-Key.

## Implications for the design
| Requirement | Consequence | Handled in 8B? |
|---|---|---|
| `user_id` is the only scope | maps to a GUPI context set; retrieval is already scoped | yes: `contexts` argument |
| Speakers | `role` is all that arrives; a speaker's name may be only in the text | **risk:** authorship expansion may lose its anchor. Needs checking on real Add payloads |
| Message ordering | order and timestamps are given | neighbours work |
| Evidence output | a ranked list of plain text | `EvidenceSet` renders to text with its qualifications; no change needed for an adapter |
| Add must finish synchronously | extraction on Add is allowed but must finish within the timeout | later decision |
| Public endpoint and TypeDB | a small hosted service plus TypeDB; capacity declared in advance | operational cost for 8E |
| Retrieval depth | `top_k = 100` | `Budget.k` is a parameter |

## Uncertain or not found
| Question | Status |
|---|---|
| Next cycle dates, and whether off-cycle evaluation exists | **not found.** Ask contactus@agentmemoryleaderboard.ai |
| Overall score weighting across data sources | not found on the pages checked |
| Answer and judge model names | configured by environment in the public code; not published |
| Rules on external calls beyond "external answer sources" | not found. Model rule above is the only one |
| Whether precomputing from the public corpora is allowed | hard-coding is banned; indexing data delivered through Add is expected. Anything else needs asking |
| Whether LoCoMo-Refined differs from our `locomo10.json` | not checked; its data is delivered through the API |
| LoCoMo licence and commercial use | **unresolved in GUPI** (`docs/known-issues.md`); entering a public leaderboard that uses it is an owner decision |
| Secondary-source dates (late July, early August) | superseded by the official Cycle 2 dates above |
