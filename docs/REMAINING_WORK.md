# Remaining work before final release

M0–M6 are merged into main. This is the outstanding scope, not a claim that the project is finished. The MIT license has been selected. The local-provider adapter is implemented and merged; real-model quality remains unqualified. These broader milestones are outside the short demo scope; use [DEMO.md](DEMO.md) for the demo.

## M7 — Product capabilities

- [ ] **Configurable profiles/rubrics:** versioned templates for expected sections, rule/severity switches, lexicon, weights, and required artifacts. Preserve configuration snapshots and detect incompatible comparisons.
- [ ] **Complete exports:** downloadable PDF/DOCX reports and trace JSON matching the selected run, evidence, scope, scores, and decisions. Print and trace CSV already exist.
- [ ] **Corrected-document output:** apply accepted paragraph/table edits to a new DOCX while preserving originals; explicitly report unsupported spans. Provide an editable reconstruction or change list for PDF input.
- [ ] **Collaboration:** project memberships with owner/editor/reviewer/viewer permissions, comments, finding assignments, and in-app notifications. Test every role/action combination and concurrent updates.
- [ ] **Classroom workflow:** courses, assignments, rubric snapshots, explicit submitted revisions, and instructor access limited to supervised submissions.
- [ ] **Semantic trace evaluation:** benchmark local embeddings/reranking against the lexical baseline on held-out labelled links. Enable only if results justify it; retain model versions and evidence.
- [ ] **Draft acceptance tests:** requirement-linked acceptance criteria and Given/When/Then proposals, labelled assumptions, and human approval before export.
- [ ] **Private processing completion:** integrate and document the local adapter, validate actual model output, test network boundaries, and qualify its deployment setup. Offline deterministic analysis already exists.
- [ ] **Impact coverage:** extend existing requirement-to-architecture paths to generated/accepted tests and qualify stale-path behavior.

## M8 — Deployment and operating readiness

- [ ] Production static frontend/proxy instead of Vite; non-root services, private storage, runtime secrets, health checks, and documented resource limits.
- [ ] Consistent database/artifact backup and restore drill, rollback procedure, retention/account deletion checks, and cache/export cleanup verification.
- [ ] Structured operational metrics for queue age, worker health, failures, latency and resource use; redacted logs and actionable troubleshooting.
- [ ] Repeatable demo setup for the current schema. The dashboard sample works; the obsolete seeder was removed because it imported nonexistent assignment/submission models and bypassed migrations.
- [ ] Fresh-machine installation and production-like deployment from the documented commands.
- [ ] Re-run the full security, PostgreSQL, worker-recovery, browser, dependency and secret-scanning gates after M7 changes.

## M8 — Evidence still needed

- [ ] Representative held-out corpus: target 50 documents, 1,000 requirement occurrences and 100 PlantUML fixtures, split by document family with independent labels.
- [ ] Publish extraction/rule/trace precision and recall by format and rule, including failures and uncertainty. Existing development fixtures are insufficient for broad accuracy claims.
- [ ] Independently review AI rewrites for usefulness and intent preservation; record critical errors and reviewer disagreement.
- [ ] Measure latency and throughput under the proposed 20-user/four-worker workload on documented hardware. Targets are in the implementation plan.
- [ ] Manual screen-reader and native zoom/keyboard review across primary journeys. Existing axe checks and responsive screenshots are partial evidence.
- [ ] Usability sessions with five representative participants; aim for at least four completing the core journey unaided, then fix and retest blockers.

## Recommended sequence

1. Finish exports/corrected-document output and configurable rubrics.
2. Add and test collaboration/classroom access controls.
3. Finish private inference and evaluate semantic/test-generation features.
4. Harden deployment, rehearse restore, and qualify the integrated release.
5. Publish actual benchmark/usability evidence and release notes; merge only after CI passes.

The full scope and acceptance targets remain in [the implementation plan](archive/PROJECT_IMPROVEMENT_PLAN.md). OCR, enterprise SSO, object storage and deep issue-tracker integrations are later extensions, not requirements of this release.
