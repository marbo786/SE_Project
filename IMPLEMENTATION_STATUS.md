# Implementation status

Branch: `codex/project-improvements`. Changes are committed and pushed after verified phase checkpoints.

| Phase | State | Evidence |
|---|---|---|
| M0: reproducible baseline and regressions | Automated baseline ready; visual baseline pending | Baseline commit `1213630` passed GitHub CI. Isolated fixtures, strict audit regressions, pinned test dependencies and local check command. Rendered review remains required for M6/M8. |
| M1: security and setup | Implemented; remote qualification pending | 40 passing tests, six remaining analysis expected failures. Shared ownership checks, revocable cookie sessions, CSRF, Argon2 upgrade, reset/verification, shared quotas, bounded document subprocesses, safe upload replacement, explicit migrations, Python 3.13/Node 24 and same-origin proxy. Local real-HTTP signup/upload/logout and frontend build passed; Python and npm audits found zero known vulnerabilities. Linux Compose and history secret scan run in CI before sign-off. |
| M2: analysis correctness | Pending | |
| M3: revisions and history | Pending | |
| M4: durable jobs | Pending | |
| M5: AI reliability | Pending | |
| M6: review workspace | Pending | |
| M7: product features | Pending | |
| M8: release qualification | Pending | |

Accuracy, load, accessibility, and usability targets remain unverified until measured.
