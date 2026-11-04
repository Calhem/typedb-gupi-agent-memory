# Developer-authored engineering fixtures (set DEV): not evaluation evidence

Written by hand by the developer to exercise `model:candidate-v1` and the Phase 7B offline harness. The
people and organisations are fictional.

| File | Contents |
|---|---|
| `passages.csv` | 26 passages (annotation-template format) |
| `assertions.csv` | 24 gold assertions, checked by hand by the developer (not independently annotated); 2 passages are negative controls |
| `responses.json` | 26 recorded **model-shaped** responses, also written by hand. They are not model output. 10 are deliberately faulty, as listed under `faults` |

**Not to be described as independent evidence.** Every figure computed on these files shows that the code
behaves as designed, not how well any extractor generalises. See docs/evaluation/phase-7b/development-fixtures.md.
