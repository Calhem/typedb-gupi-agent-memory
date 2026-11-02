# Annotated conversation fixtures

Synthetic conversations (all people and organisations invented) with hand-written gold annotations, used
to evaluate extraction (`python -m gupi.evaluation`).

- `dev/`: rules and prompts may be developed against these.
- `heldout/`: committed before any extractor rules were written; results are reported once and the
  extractor is not tuned on them afterwards.

Gold conventions:
- `roles` name players by their surface text in that message; `values` are attribute values.
- `start` / `end` are `[earliest, latest)` date windows (ISO dates) or null for unknown.
- `ongoing: true` means the message states the fact still holds when written (present tense, "still",
  "now"); a past-tense report with no end ("joined in March") leaves the end unknown (`ongoing: false`).
- A pronoun subject ("She ...") is annotated with the person it refers to; extractors without
  coreference are expected to miss it.
