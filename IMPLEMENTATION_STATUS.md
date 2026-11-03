# Implementation status

Branch: `codex/project-improvements`. Changes are committed and pushed after verified phase checkpoints.

| Phase | State | Evidence |
|---|---|---|
| M0: reproducible baseline and regressions | Automated baseline ready; visual baseline pending | Baseline commit `1213630` passed GitHub CI. Isolated fixtures, strict audit regressions, pinned test dependencies and local check command. Rendered review remains required for M6/M8. |
| M1: security and setup | Verified and pushed (`958a727`) | 40 passing tests, six analysis expected failures at this checkpoint. Ownership, revocable sessions, CSRF, Argon2 upgrades, recovery/verification, quotas, bounded upload validation, explicit migrations and same-origin proxy. Local HTTP smoke passed. GitHub run `41529888698` passed backend tests, Linux Compose signup/upload/logout, frontend build, Python/npm audits, and history secret scan. |
| M2: analysis correctness | Implemented and locally verified; remote qualification pending | Full suite: 70 passing, one remaining repair expected failure; final parser/evaluator subset: 11 passing including an additional regression. Ordered DOCX/PDF extraction, occurrence IDs/source spans, UML aliases/receiver operations, exact ID matching, cycle-safe tracing and scoped rubric v2. Empty/partial inputs are not graded; decisions cannot change raw scores; failed reanalysis preserves results. Reports poll and show score applicability/evidence. Real HTTP upload-to-score/evidence flow and frontend build passed. Independent annotation/accuracy remains a release gate; legacy-label disagreements are published explicitly. |
| M3: revisions and history | Pending | |
| M4: durable jobs | Pending | |
| M5: AI reliability | Pending | |
| M6: review workspace | Pending | |
| M7: product features | Pending | |
| M8: release qualification | Pending | |

Accuracy, load, accessibility, and usability targets remain unverified until measured.
