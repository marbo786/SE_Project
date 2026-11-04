# Implementation status

Branch: `codex/project-improvements`. Changes are committed and pushed after verified phase checkpoints.

| Phase | State | Evidence |
|---|---|---|
| M0: reproducible baseline and regressions | Automated baseline ready; visual baseline pending | Baseline commit `1213630` passed GitHub CI. Isolated fixtures, strict audit regressions, pinned test dependencies and local check command. Rendered review remains required for M6/M8. |
| M1: security and setup | Verified and pushed (`958a727`) | 40 passing tests, six analysis expected failures at this checkpoint. Ownership, revocable sessions, CSRF, Argon2 upgrades, recovery/verification, quotas, bounded upload validation, explicit migrations and same-origin proxy. Local HTTP smoke passed. GitHub run `41529888698` passed backend tests, Linux Compose signup/upload/logout, frontend build, Python/npm audits, and history secret scan. |
| M2: analysis correctness | Verified and pushed (`0aefd44`) | GitHub run `41683123659` passed all jobs, including Compose upload-to-score/evidence. Final suite has 71 passing tests and one repair expected failure. Ordered extraction, occurrence IDs/source spans, normalized UML, cycle-safe tracing, scoped rubric v2, transactional publication, score/source UI and polling. Independent annotation/accuracy remains a release gate; legacy-label disagreements are published explicitly. |
| M3: revisions and history | Local checks passed; GitHub CI pending | 81 backend tests pass; PostgreSQL skips locally and the M5 repair regression remains expected. Frontend production build, Python/npm audits and Chromium draft-to-history workflow pass. Immutable runs, concurrent drafts, replay-safe requests, extraction correction, reviews, comparisons and retention. Rehearsal on a local database copy preserved 2 users, 12 projects, 22 files, 150 findings and 12 scores. PostgreSQL migration/concurrency and browser workflow are CI gates. |
| M4: durable jobs | Pending | |
| M5: AI reliability | Pending | |
| M6: review workspace | Pending | |
| M7: product features | Pending | |
| M8: release qualification | Pending | |

Accuracy, load, accessibility, and usability targets remain unverified until measured.
