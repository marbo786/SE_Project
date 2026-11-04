# Implementation status

Verified checkpoints are pushed on `codex/` branches and merged into `main` after GitHub checks pass.

| Phase | State | Evidence |
|---|---|---|
| M0: reproducible baseline and regressions | Automated baseline ready; visual baseline pending | Baseline commit `1213630` passed GitHub CI. Isolated fixtures, strict audit regressions, pinned test dependencies and local check command. Rendered review remains required for M6/M8. |
| M1: security and setup | Verified and pushed (`958a727`) | 40 passing tests, six analysis expected failures at this checkpoint. Ownership, revocable sessions, CSRF, Argon2 upgrades, recovery/verification, quotas, bounded upload validation, explicit migrations and same-origin proxy. Local HTTP smoke passed. GitHub run `41529888698` passed backend tests, Linux Compose signup/upload/logout, frontend build, Python/npm audits, and history secret scan. |
| M2: analysis correctness | Verified and pushed (`0aefd44`) | GitHub run `41683123659` passed all jobs, including Compose upload-to-score/evidence. Final suite has 71 passing tests and one repair expected failure. Ordered extraction, occurrence IDs/source spans, normalized UML, cycle-safe tracing, scoped rubric v2, transactional publication, score/source UI and polling. Independent annotation/accuracy remains a release gate; legacy-label disagreements are published explicitly. |
| M3: revisions and history | Verified; merged into `main` through PR #1 (`fb47484`) | All five GitHub jobs passed in runs `41729968969` and `41730088663`, including PostgreSQL migration/concurrency and Linux browser workflow. Local database-copy rehearsal preserved 2 users, 12 projects, 22 files, 150 findings and 12 scores. |
| M4: durable jobs | Verified; merged through PR #2 (`e7196f7`) | GitHub runs `41836092569` and `41836138303` passed all five jobs, including Compose recovery and duplicate delivery. 89 tests pass, PostgreSQL skips locally, one known M5 repair expected failure. Transactional outbox, leased attempts, extraction checkpoints, cancellation, bounded worker-loss recovery, native local worker and Celery/Redis/PostgreSQL Compose. Real worker/API kill-and-restart test and Chromium workflow pass; Python audit reports no known vulnerabilities. |
| M5: AI reliability | M5a local checks passed; GitHub verification pending | Full local suite: 103 passed, 1 PostgreSQL skip; all 17 AI safety tests separately passed after four additional cases, and frontend build passed. Raw caching disabled, outbound redaction, bounded attempts, failed-call budget reservations, safe errors, occurrence coverage validation, conservative rewrite checks and visible review checklist. Remaining M5 scope is listed in `docs/AI_SAFETY.md`. |
| M6: review workspace | Pending | |
| M7: product features | Pending | |
| M8: release qualification | Pending | |

Accuracy, load, accessibility, and usability targets remain unverified until measured.
