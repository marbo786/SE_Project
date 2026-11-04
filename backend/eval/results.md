# Deterministic legacy-fixture evaluation

33 authored examples; counts use occurrence IDs, including every missing/duplicate ID.

These labels are preserved from the original dataset, not relabelled to match the new code. FR-411 now applies to performance/availability thresholds; legacy labels also required numbers in other NFR subtypes. The resulting disagreements need independent annotation review. This is a development fixture, not a held-out accuracy or AI evaluation.

| Rule | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| FR-401 | 10 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| FR-402 | 5 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| FR-409 | 5 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| FR-410 | 6 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| FR-411 | 3 | 0 | 7 | 1.00 | 0.30 | 0.46 |

Mismatch details are recorded in `results.json`. Broader parsing, UML, traceability and scoring cases are integration/regression tests; their pass count is not an accuracy percentage.
