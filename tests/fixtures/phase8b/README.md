# Phase 8B claim-path fixture (G1): exploratory

**Developer-authored by the same agent that wrote the retrieval code, with the design in mind. It can show that a
mechanism works when useful claims exist. It is not independent validation, and says nothing about whether GUPI can
create such claims from arbitrary conversations.** All names and events are invented. No benchmark content.

- `world.json`: messages by thread, each with the extraction that the candidate pipeline receives as a recorded
  response. Claims therefore pass through `model:candidate-v1.1`, Stage 4 protections and `formation:v1`. No claim is
  inserted directly, and no review item is approved by the runner.
- `questions-dev.json` (40) and `questions-sealed.json` (20): a fixed split, one third of each class, seed 20261106.
  Sealed questions are scored once, after the code is frozen.
- `SCORING.md`: rules, written before any claim-path code.
- `MANIFEST.sha256`: hashes. These files are frozen: a change is a new version.

**Identity:** referents are scoped per thread (`extraction/contract.py`), so claims connect across threads only through
accepted identity claims. A simulated reviewer accepts the same-name suggestions, except `never_merge`.
