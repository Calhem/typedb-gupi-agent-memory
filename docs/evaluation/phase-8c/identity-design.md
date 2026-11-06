# Phase 8C.2: identity across sessions

**The smallest mechanism that reuses what exists.** No new schema, entity type or framework. Identity is still an
`identity` claim, a hypothesis until a person accepts it (ADR 0006).

## Three cases, three treatments
| Case | Example | Treatment |
|---|---|---|
| **The same platform speaker** | AML `user_id` + `role`; a LoCoMo speaker | one referent (`identity.participant_id`). The platform states this, so nothing is inferred and nothing is merged. Sessions stay separate contexts |
| **A shared name, nothing else** | "Alex Reed" in two sessions | **no link is recorded and retrieval never crosses.** Reported as `name_only` |
| **A shared name plus a second signal** | both "Alex Reed"s are tied by claims to Fenwick Labs; or a speaker of that name is in the session | a **hypothesis** identity claim, `identity:session-link:v1`, with the reason in words. Never accepted automatically |

**Why not simply trust names inside one user?** One person can know two Alexes. Exact names are enough to *propose* a pair
and never enough to *justify* one.

**What counts as a name match:** the exact name, or a single word that is the first word of a fuller name. "Jo" and
"Josephine Hale" do not match: that needs a reviewer, because guessing nicknames would be inference from similarity.

## How it behaves
| Requirement | Behaviour | Test |
|---|---|---|
| Session boundaries | contexts are untouched; a referent is still per session | `test_a_platform_speaker_key…` |
| Users are never compared | the caller passes one user's sessions | `test_two_people_with_one_name…` |
| Same name is not identity | no signal, no link | `test_a_shared_name_alone_links_nothing` |
| Accepted links work | a reviewer's acceptance joins spells, and a departure in another session then counts | `test_uncertain_links_never_change_an_answer` |
| Ambiguity is preserved | a hypothesis changes no answer, and two groups stay two | same test |
| Explainable | every link holds its reason and two pieces of evidence | `test_a_second_signal…` |
| Aliases | first name to full name with a signal; nicknames only by review | `test_a_first_name…`, `test_a_nickname…` |
| Changing roles | after acceptance, gaps stay gaps | `test_a_changing_role…` |
| Rejections stand | never proposed again, never walked | `test_links_are_not_proposed_twice…` |
| Cross-session references | labelled on the path and on the item | `test_a_reference_across_sessions…` |

## Retrieval
`Budget.unresolved_links` is **off by default**. When on, a second hop may cross a hypothesis link, but the hop's tier
is `unresolved`, and evidence reached only that way is labelled "identity not confirmed". A link with any evidence
outside the question's scope is ignored. Without a reviewer, this is the only way a third party can connect across
sessions, so it is evaluated as its own variant, C+, not silently folded into C.

## A bug this work found
**Since Phase 8B, an accepted identity could walk a path into another user's conversation and return its text.** The 8B
fixture has one user, so nothing showed it, and AML prohibits retrieval across `user_id`. Retrieval now returns only
observations inside the question's scope, and a hop with no in-scope evidence is dropped. The regression test fails
without the fix. All 8B development rankings are unchanged.

## Limits
- A wrong link is possible, by design, as a labelled hypothesis. C+ can return the wrong person's evidence with a
  warning, and whether an answering model heeds the warning is what 8C.4 tests.
- **AML's speaker shape is not established.** Its LoCoMo answer template has separate memories per speaker, which may
  mean one `user_id` per speaker. Only the Add payload can settle it, and retrieval across `user_id` is prohibited.
- `suggest()` from Phase 3 is unchanged and unscoped. An AML adapter must use `link_sessions`, not it.
