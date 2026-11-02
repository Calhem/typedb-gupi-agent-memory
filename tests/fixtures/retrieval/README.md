# Retrieval benchmark (frozen)

A small synthetic world (people and the company "Halden" are invented) and questions with gold answers,
used by `python -m gupi.retrieval_eval`. Committed before the query code was written; not to be tuned on.

`world.json`: three conversations in the extraction-fixture format (messages with gold claims), plus
review decisions: every gold claim is accepted except where `decision` says `rejected` or `unreviewed`.
Messages are received one hour after they were said and reviewed one hour after that. Identities between
referents with exactly the same name are accepted on 2025-09-01.

`questions.json`: each question names a claim type, fixed roles by name, at most one open role (null),
optional attribute values, a valid time and a belief time (default 2025-10-01). Gold:
- `answer`: TRUE, FALSE, UNKNOWN, NOT_YET_KNOWN or CONTESTED, judged from the evidence with GUPI's stated
  conventions: an unstated start or end is unknown; "joined" without a leaving date leaves the end
  unknown; a start in one statement and an end in another describe one spell unless something says
  otherwise; rejected and unreviewed claims are not evidence; nothing said is NOT_YET_KNOWN.
- `binding`: for open questions, the name that fills the open role when the answer is TRUE.
- `evidence`: message keys a correct answer should cite (scored only for TRUE, FALSE and CONTESTED).
