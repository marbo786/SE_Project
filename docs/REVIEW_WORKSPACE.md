# Review workspace (M6)

The workspace keeps reports attached to a selected run and corrections attached to a draft. A newer failed or partial attempt does not replace an earlier successful report. The analysis-history selector exposes both.

## First review

1. Use **Try a sample review** on the dashboard to download the synthetic library SRS, or bring a DOCX/text PDF.
2. Create a project, select requirements-only or architecture scope, and choose deterministic or configured AI checks. Architecture scope requires use-case, sequence, and class diagrams.
3. Save the sources. Upload progress distinguishes sending bytes from server validation. If a request is interrupted, retry from the same form; its saved project and upload idempotency keys are reused. Saved drafts can also be reopened from Projects. This is request retry, not byte-range upload resumption.
4. Extract and inspect requirement counts, warnings, source locations, IDs, text, and classification. Save corrections and confirm the evaluated scope before starting analysis. **Restore original text** reverses a text correction in the draft.
5. The run view reconnects after refresh, polls active work every two seconds with bounded error backoff, pauses background polling, and stops on terminal state. Partial, failed, cancelled, and ungraded results have distinct messages.
6. Review prioritized findings, open source excerpts, and record accepted/dismissed/needs-review decisions. Rewrite suggestions show a text diff and validation evidence; applying one requires explicit human intent confirmation and creates/updates a draft.
7. Branch a draft, revise, analyze, and compare. Requirement additions/removals/changes, finding changes, incompatible rubric/scope notices, and current architecture paths are shown separately.

## Review annotations and history

Finding and trace decisions use the last decision ID for optimistic concurrency. Concurrent changes produce a conflict instead of silently overwriting another decision. Manual trace links validate both typed endpoints against the selected report's extracted snapshot, require an evidence note, and deduplicate identical endpoints under the project write lock. Rejecting a manual link removes it from accepted paths while preserving the audit record.

Manual links and review decisions are annotations: they do not mutate `AnalysisRun.report` or recalculate its machine score. CSV uses the current review projection. Print includes all findings and traces regardless of the active tab, search, or filters. Source references, category scores, weights, contributions, coverage, and run identifiers accompany the result. Separate downloadable PDF/DOCX and corrected-source exports belong to M7.

Project details expose rename, archive/restore, and a revision timeline. Archived projects remain readable and can be found with **Show archived projects**. Writes require restoration. Rename compares the last displayed name before saving. Project/revision/run identities are independent of display names.

Tabs, search, severity, review state, trace status, selected source finding, comparison run, and selected report use URL parameters. Light/dark appearance and comfortable/compact spacing are local display preferences; credentials are never stored there. Expired sessions clear cached protected data and return to the requested workspace after sign-in.

## Contracts and checks

`scripts/generate_api_types.py` generates TypeScript schema types from the application's OpenAPI without a network dependency. Revision/run responses have explicit Pydantic response models. The client consumes generated types for those responses and for project/draft/requirement/review commands. Parser/report projections retain feature-specific interfaces because their versioned evidence dictionaries are heterogeneous. CI checks that generated types are current.

```powershell
.\.venv313\Scripts\python.exe scripts/generate_api_types.py --check
.\.venv313\Scripts\python.exe -m pytest backend/tests -q
npm --prefix frontend run build
.\.venv313\Scripts\python.exe scripts/check_http_local.py --browser
```

The HTTP/browser command creates disposable accounts, database, storage, API, worker, and Vite processes; it does not operate on the local user's projects. On Windows it requires process, temporary-file, and local-socket permissions.

Browser coverage combines a real extraction → correction → analysis → draft/history journey with controlled API fixtures for failures, UI states, and accessibility. Fixtures test interrupted upload retry without duplicate project creation, session expiry, queued-to-partial polling, terminal polling stop, persisted filters, keyboard disclosures, finding decisions, complete print despite filters, mobile drawer focus return, and layout at 360/768/1440px and 200% root text size. The text-resize check is not a substitute for every browser's native zoom behavior. Axe checks the report in both themes and the mobile draft. Screenshots and failure traces are in `frontend/test-results`.

## Remaining release qualification

Automated accessibility checks and rendered screenshot inspection do not establish WCAG 2.2 AA conformance. Manual screen-reader testing, a broader keyboard/zoom matrix, representative participant usability, and production-scale performance remain M8 acceptance evidence. No independent accuracy or usability score is claimed by this milestone.

Run/revision selectors currently show the newest 100 entries; individual older run URLs remain usable. Complete history pagination and very large report rendering should be qualified before deployments that exceed that working set. No score trend is plotted across potentially incompatible runs.
