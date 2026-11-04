# SRS Reviewer project review

Reviewed on 2 November 2026 against local HEAD and GitHub `main`, both at `64dfaf143af2799b511aca99558f01ee792769a3`.

## Verdict and scope

**Overall engineering assessment: 5.5/10. Academic prototype: 7/10. Readiness for a public multi-user deployment: 3/10.** These are judgment-based ratings, not an automated average or a prediction of a course grade.

The idea is useful and the project has a coherent foundation: a React/TypeScript client, FastAPI API, SQLAlchemy models, Alembic migrations, configurable deterministic rules, an LLM provider boundary, traceability review, CSV export, and version comparison. The largest weakness is trustworthiness. Several normal inputs produce incorrect findings, the repair validator can approve meaningless output, and users can access other users' findings and traceability records.

The review covered application source, schemas, models, migrations, parsers, rules, scoring, LLM handling, frontend routes/components/pages, Docker configuration, CI, tests, evaluation scripts/data, README, feasibility report, and repository organization. Historical patch scripts were inventoried; they are not part of the normal runtime. GitHub metadata, recent commits, recent CI runs, and issues/PR collections were inspected. No application source was changed.

Verification:

- `npm run build`: passed, TypeScript and Vite production build.
- Backend suite: **11 passed, 8 deprecation warnings**, using existing installed dependencies, an isolated review database, mock provider, and pytest-asyncio. The first sandboxed attempts stalled while Windows created an asyncio socket pair; the suite passed outside that sandbox. This was not a fresh dependency installation.
- Latest GitHub CI: [successful run](https://github.com/marbo786/SE_Project/actions/runs/38301411800). The four preceding runs returned by the recent-runs query failed.
- Synthetic parser, scoring, pipeline, repair, and HTTP authorization probes reproduced the issues identified below. These used synthetic data and isolated databases, without a live Groq call.
- The root `tests/test_e2e_flow.py` was inspected, not executed against the existing application database. It is not included in the current backend CI test command.
- Rendered UI inspection could not be completed. The embedded browser could not reach localhost, and Windows computer use stopped because it could not confidently determine the browser URL. Visual, responsive, keyboard, and print assessments below are based on code and require browser verification.
- No load test, live LLM accuracy evaluation, production deployment test, or complete transitive dependency audit was performed.

## Scorecard

| Area | Rating | Assessment |
|---|---:|---|
| Problem choice and product usefulness | 8/10 | Clear educational and engineering value; cross-artifact review is a useful differentiator. |
| Visual design, provisional | 6.5/10 | Consistent technical theme, typography, components, and severity styling; dense small text and repeated hardcoded styling. |
| UX and workflow completeness | 4.5/10 | Upload wizard and filters exist; analysis progress, recovery, editing, and score visibility are incomplete. |
| Frontend engineering | 5.5/10 | Strict TypeScript and reusable primitives; duplicated data/auth logic, weak error handling, no frontend tests. |
| Backend organization | 6/10 | Sensible modules and provider separation; HTTP, orchestration, persistence, and lifecycle concerns still overlap. |
| Data model and versioning | 4.5/10 | Basic relations/migrations exist; versions depend on names and analysis runs are overwritten. |
| Parsing and deterministic correctness | 4/10 | Works for narrow supported examples; ordinary tables, aliases, and method syntax expose defects. |
| LLM and repair reliability | 4/10 | Structured checks, retries, logging, and repair attempts exist; validation and privacy boundaries are incomplete. |
| Security and privacy | 2.5/10 | Password hashing and JWT verification exist; confirmed cross-user data access and mutation are release blockers. |
| Testing and evaluation | 4/10 | Green CI and a small suite; important behavior is untested and some tests accept wrong behavior. |
| Deployment and operations | 3/10 | Development containers exist; configuration mismatch, no durable jobs, limited health checks/observability. |
| Documentation and repository hygiene | 5/10 | Useful README and architecture overview; stale demo script, overstated benchmark scope, patch-script clutter. |

## Confirmed defects and high-priority gaps

### 1. Cross-user access and modification — critical, reproduced through HTTP

`backend/app/routers/findings.py:14` and `backend/app/routers/traceability.py:17`, `:22`, and `:36` authenticate a user but do not establish ownership of the referenced project/link.

Using a token for a second synthetic user:

| Request targeting the owner's records | Result |
|---|---|
| `GET /projects/1` | 404, correct ownership filtering |
| `GET /findings/project/1` | 200 with owner-only finding text |
| `GET /traceability/project/1` | 200 with owner's links |
| `GET /traceability/project/1/export` | 200 with owner's CSV |
| `PATCH /traceability/1` | 200; owner's link changed to rejected |

Centralize an owned-project dependency and resolve link ownership through its project. Apply it to every nested resource and export. Add two-user isolation tests covering reads, mutations, exports, and nonexistent IDs. Authentication alone is insufficient.

### 2. A missing requirement ID crashes trace linking — high, reproduced

`backend/app/pipeline/checks/traceability_checks.py:55` uses `req_id in uc_name`. The parser returns `None` for an unidentified requirement. A requirement without an ID plus a use-case model raises `TypeError: 'in <string>' requires string as left operand, not NoneType` rather than completing with an ordinary missing-ID finding.

Use an internal non-null requirement identity distinct from the user-authored ID; guard optional authored IDs and avoid substring matching for identifiers. `FR-1` should not automatically match `FR-10`.

### 3. DOCX table requirements are split incorrectly — high, reproduced

In `backend/app/pipeline/srs/parser.py:71`, paragraphs are processed before all tables, losing document order. Each table cell is then treated independently. A normal two-column row containing `NFR-01` and `The system shall respond within 200ms.` becomes two requirements: an ID-only requirement and a statement with no ID.

This creates false missing-ID and metric findings and can trigger the trace-link crash. Preserve document block order and parse each table row using column semantics. Keep the ID, statement, classification, and location together.

`backend/tests/test_parser.py:58` currently asserts the ID-only text, so it protects the defect instead of detecting it.

### 4. Valid PlantUML generates false defects — high, reproduced

- `usecase "Login" as UC1` followed by `User --> UC1` is reported as a disconnected Login use case. Use-case aliases are discarded by `backend/app/pipeline/uml/parser.py`, while relationships retain the aliases.
- A class declaring `+login()` and a sequence message calling `login()` is reported as an undefined operation. `backend/app/pipeline/checks/uml_checks.py:127` attempts to match a word at the beginning of `+login()` and fails on the visibility marker.

Normalize aliases and symbols into stable element identities. Parse visibility, parameter lists, and return types before comparing operations, and compare against the receiving class rather than one global set of method names. Publish a supported syntax contract and return explicit unsupported-syntax warnings.

### 5. Meaningless rewrites can be marked verified — high, reproduced

`backend/app/pipeline/repair.py:82` validates a fabricated requirement with `class='unknown'`, bypassing the non-functional metric rule. It checks only a subset of deterministic findings and does not require the output to preserve the original behavior or even contain a normative requirement statement.

A synthetic provider returning `{"rewrite_suggestion":"Hello."}` for a defective NFR produced `rewrite_passed=true`. The frontend displays that flag as **VERIFIED PASSED**.

Keep the original classification, requirement context, related conflicting requirements, and stable identity. Validate structure, metrics, preservation of intent, and relevant cross-requirement constraints. Label the result precisely, for example “Passed 3 automated checks; human review required.” Do not present lexical validation as semantic verification.

### 6. Scores reward missing evidence and change after confirmations — high, reproduced

- An entirely empty project can be analyzed through the API and ends with `status='done'`, **60/100 overall**, including full UML and traceability category weights. `compute_scores` defaults empty categories to full credit.
- In an isolated pipeline with four requirements, three matching use cases, and one unlinked requirement, confirming the three links and re-running the same analysis changed the traceability contribution from **25/30 to 15/30**, despite retaining the same three links and the same missing-link defect. `backend/app/pipeline/analyzer.py:198` counts only newly suggested links, excluding retained confirmed/rejected records.
- Omitting the use-case artifact skips traceability checks entirely, including otherwise useful requirement-to-class/sequence matching.
- Scores are persisted but are absent from the current project response schema and report UI.

Model category applicability and evidence explicitly. Use stable eligible element counts, expose coverage separately from defect density, and distinguish “not evaluated” from “passed.” Store the rubric and rule versions with each result. Present raw category percentages separately from weighted contributions.

### 7. The frontend can stay on an unfinished report — high, source-confirmed

`frontend/src/pages/ReportPage.tsx:247` performs one initial fetch. There is no polling or event subscription while analysis runs. New-project creation navigates to the report immediately after the background task is scheduled.

The user can remain on an analyzing report with no findings until manually reloading. The empty state says all rules passed whenever the findings array is empty, without checking that a complete successful analysis actually occurred. Failed project/findings requests do not receive a coherent error state, and traceability failures are swallowed.

Poll only while the job is active, or use server-sent events. Show queued/parsing/rules/AI/traceability/completed/partial/failed stages. Distinguish loading, failed, not evaluated, no findings, and no filter matches. Provide retry and reanalyze actions.

### 8. Docker Compose and frontend API ports disagree — high, configuration-confirmed

`docker-compose.yml:9` exposes the backend on host port **8001**, while `frontend/src/lib/api.ts:4` defaults to **http://localhost:8000**. Compose does not set `VITE_API_URL`. The `/api` proxy exists in Vite config but the client bypasses it.

Use a same-origin `/api` URL and correct proxy targets for local development and containers, or explicitly configure the public API origin. Add a Compose smoke test. A remote deployment also cannot use the visitor's localhost as its backend.

### 9. Weak input and upload validation — medium/high, partially reproduced

- An invalid DOCX made only of `PK` plus arbitrary bytes was accepted with HTTP 200. Checking two ZIP signature bytes does not validate an Office document.
- The register endpoint accepted an empty name and empty password with HTTP 200. Browser-required fields do not protect direct API callers.
- Uploads read the entire file before enforcing the size limit. Compressed document expansion, page counts, and parse time are not bounded.
- UML uploads validate extension but not parseability or a useful non-empty model.
- Project creation accepts empty names and lacks practical field bounds; signup/login/analysis have no rate limiting or per-user quotas.

Validate document structure, require useful extraction, cap request bytes before full buffering, bound decompressed work, and isolate parsing time/resources. Validate API schemas with length constraints and normalized names/emails. Rate-limit authentication and expensive analysis separately.

### 10. Source references disappear — medium, reproduced

Rules produce `source_ref`, and the database/schema support it. The finding constructor in `backend/app/pipeline/analyzer.py` never copies it into the saved Finding. A pipeline probe returned only null source references. The frontend contract also does not expose them in its finding interface.

Persist provenance and provide a source panel showing page/paragraph/table row and the highlighted original text. This is central to making findings actionable.

### 11. Demo seeding is broken — medium, source-confirmed

`backend/scripts/seed_demo.py` imports removed Assignment and Submission models and passes removed role/submission fields. Both model modules are absent. Rewrite it around current User/Project/Artifact models or remove it from supported workflows.

## Frontend and UX improvements

The consistent dark engineering theme, restrained status colors, reusable primitives, skeletons, file wizard, finding search, severity filtering, comparison view, and trace confirmations provide a useful base. Keep those concepts.

Improve the information hierarchy first:

1. Open a completed report with an understandable summary: what was analyzed, extraction counts, evaluation coverage, score breakdown, top problems, and analysis limitations.
2. Let users open a finding beside the source text, then inspect or edit a proposed correction with a visible diff.
3. Add finding workflow states such as open, acknowledged, false positive, accepted correction, and resolved. Keep reviewer reasons and timestamps.
4. Add artifact management: view uploaded filenames, preview parsed requirements/UML, replace a file, remove an artifact, start another revision, and retry failed stages.
5. Give uploads immediate size/type feedback, per-file progress, safe retry, and a saved draft. Current retry after a late failure creates another project; duplicate UML types appear as separate attachments in the wizard but overwrite one another on the backend.
6. Offer a genuine traceability matrix or graph with confidence and evidence. The current table is a list of links, and reviewers cannot create a missing link manually through the UI.
7. Export a complete report containing scores, scope, findings, sources, decisions, and run metadata. Current CSV export covers trace links; browser print renders only the current conditional tab/content.

Readability and accessibility work, based on code:

- Most application text is 10–12px and many controls are only 20–32px high. Increase ordinary body size, use a clearer heading hierarchy, and offer a comfortable density setting.
- Replace phrases such as “Ingest Specification,” “Operator,” and “Inspection Telemetry” with plain product language unless target-user testing supports the current terminology.
- Repair keyboard access for the file drop zone and finding expansion; the expansion click handler sits on a div while its nested button does not own the handler. Add `aria-expanded`, tab semantics, accessible names for icon-only controls, and live announcements for job/error states.
- The mobile menu is fixed over the top-left content without a corresponding reserved header area. Tabs do not wrap or scroll explicitly. Verify narrow viewports, zoom, focus management, and touch use.
- Consolidate colors into semantic tokens. The stylesheet defines tokens, but most pages repeat hex literals, making global accessibility/theme changes difficult.
- Verify print layout: the sidebar is not explicitly hidden, many nested surfaces retain hardcoded dark colors, and only the active tab is mounted.
- Replace the missing `/vite.svg` favicon reference with an actual application icon.

Frontend engineering changes:

- Use the installed TanStack Query for shared server state, polling, invalidation, and request cancellation. It is configured but pages currently implement separate fetch effects.
- Keep authentication in one context. Registration and Layout logout directly modify localStorage, while the AuthProvider has its own state. Remove stale instructor-role assumptions unless roles are restored on the backend.
- Validate stored user data defensively. AuthProvider's unguarded `JSON.parse` can fail on corrupted localStorage.
- Add centralized expired-session/401 handling; the route guard currently trusts token presence only.
- Route PATCH/export calls through the same API client; check HTTP status before treating a fetch as success or downloading its body.
- Generate frontend API types from OpenAPI and split ReportPage into hooks and smaller feature components. Strict TypeScript is enabled, but `any` and duplicate hand-written contracts weaken the boundary.
- Add an error boundary and component/E2E tests for the actual user workflow.

## Backend architecture and data integrity

Keep a modular monolith. The current project does not need microservices. FastAPI plus clear analysis modules is a reasonable direction.

A stronger conceptual model is:

`User -> Project -> ProjectRevision -> Artifact -> AnalysisRun -> Findings / TraceLinks / Scores`

Add reviewer decisions and audit records as separate persistent objects linked to stable findings/elements. Use a dedicated validated LLM cache instead of using call logs as the cache store.

Specific changes:

- **Durable jobs:** FastAPI BackgroundTasks run in the API process and have no durable queue, lease, retry policy, or cancellation. Move long parsing/LLM analysis to a worker when supporting multiple users. Add atomic job claiming and idempotency so concurrent analyze requests cannot start duplicate runs.
- **Safe lifecycle:** Every API startup marks all analyzing projects as errors. In a multi-worker deployment, a newly starting worker can invalidate another worker's active work. Recover only expired job leases.
- **Preserved results:** Reanalysis deletes old findings/scores before replacement succeeds. Store immutable runs and atomically switch the current successful run rather than destroying the previous report.
- **Revision identity:** A project name currently acts as the version-family key. Equal names unintentionally group independent work, renaming is awkward, and simultaneous creates can allocate duplicate versions. Use a stable project ID, revision number, parent revision, and database uniqueness constraints.
- **Upload/result consistency:** Uploading replacements is allowed while analyzing or after a completed analysis, without invalidating the status/results. Associate immutable artifacts and hashes with a specific revision/run, and prevent races between replacement/deletion and parsing.
- **Database constraints:** Add indexed foreign keys and uniqueness for `(revision, artifact_type)` and trace identities where the chosen product model requires them. Add a real project/revision ownership boundary. Enable SQLite foreign-key enforcement for local development.
- **Database portability:** `check_same_thread=False` is passed for every configured database URL. Make SQLite-specific options conditional before a PostgreSQL migration. SQLite is fine for a small local demo; choose PostgreSQL when concurrent writes, shared deployment, and operational tooling justify it.
- **Transaction failure:** Roll back a failed database transaction before writing an error state; the current outer exception handler can fail to persist the error if the session is already failed.
- **Deployment lifecycle:** Run Alembic as a deployment/init operation rather than as an import-time mutation in every application process. Ensure CLI and application migrations use the same configured URL.
- **API behavior:** Add pagination, bounded filtering, response models for report/run summaries, sensible status codes, and predictable error shapes. Project lists currently return all records.
- **Observability:** Structured logs should include run/project/request IDs, stage durations, provider/model, attempts, token usage, and failure categories. Health endpoints should distinguish liveness from database/worker readiness.
- **Operations:** Add backup/restore documentation, artifact retention/deletion, a production static frontend server, non-root runtime containers, `.dockerignore`, and a production configuration without reload or source bind mounts. Without `.dockerignore`, local backend `.env` and other local files can be copied into a built image.

## LLM, traceability, and scoring trust

Important weaknesses beyond the reproduced validator issue:

- Testability/conflict checks redact data, but the repair loop sends original quoted text directly to the provider. Apply one privacy boundary to every external call, including explanations and retries.
- The existing redactor covers limited patterns; it is not a general guarantee that documents are safe to transmit. Give the user clear provider/mode information and an explicit deterministic-only mode.
- Cache queries are global across projects/users and use raw response logs without schema-validity markers, scope, retention, or expiry. Identical redacted prompts can share responses across users. Scope sensitive caches and track validated outputs with prompt/schema/model versions.
- Invalid JSON is cached before validation. The outer validation retry asks for the same prompt again and can retrieve the same invalid cached response. Invalidate bad entries or use a corrected prompt and a cache-bypass path.
- The default mock provider invents a non-testable `MOCK-01` result regardless of the uploaded requirement IDs. Keep mock mode obvious and out of trusted reports, and validate every returned ID against the input set.
- Testability/conflict prompts include the full requirements list with a fixed output budget. Long documents can produce truncation, omissions, or provider-limit failures. Batch testability and retrieve plausible conflict pairs while measuring what coverage is lost.
- The repair call limit counts successful, non-cache log entries; failed attempts and invalid-output work are not a reliable request/token budget. Track attempts, tokens, elapsed time, and per-user/project limits at the call boundary.
- LLM errors include raw provider error text in a saved user-facing finding. Use a safe user message plus structured internal diagnostics. Repair errors are swallowed and can leave the project marked done despite missing repair output.
- Similarity is lexical Jaccard without reliable stemming/synonyms, and inferred links do not expose confidence or evidence. Start with parser/identity fixes and an annotated trace dataset, then compare lexical matching against an embedding/reranking approach before replacing it.
- Claimed transitive coverage is incomplete: use-case-to-class links can be generated, while class coverage checks only direct requirement-to-class links. Sequence-orphan state is collected but never emitted as a corresponding orphan check.
- Confirmed links can remain after their source or target disappears. Revalidate persistent decisions against the current revision and show stale decisions separately.
- Confirming/rejecting a link does not immediately recompute findings/scores; users need consistent derived results or a visible recalculation state.

Treat parsing coverage, inferred trace confidence, deterministic findings, and AI suggestions as separate kinds of evidence. A single quality number should never hide unparsed or unevaluated material.

## Security maintenance

The repository pins `python-multipart==0.0.9`, which falls within the affected range of the maintainer's [multipart denial-of-service advisory](https://github.com/Kludex/python-multipart/security/advisories/GHSA-59g5-xgcq-4qw3). A [later header-parsing advisory](https://github.com/Kludex/python-multipart/security/advisories/GHSA-pp6c-gr5w-3c5g) is another reason to choose a currently maintained compatible version rather than stopping at the oldest historical fix.

It also pins `python-jose==3.3.0`, covered by the [algorithm-confusion advisory](https://github.com/advisories/GHSA-6c5p-j8vq-pqhj). This application's explicitly restricted HS256 configuration is not proof of exploitability through that advisory; the vulnerable package pin should still be replaced and tested. No claim is made that every advisory is reachable in this application.

Add automated dependency/secret scanning and lock transitive dependencies. Add authentication throttling, password length validation compatible with the chosen hash, safe malformed-token handling, and account recovery. For a hosted browser product, evaluate secure HttpOnly session/refresh cookies with a deliberate CSRF design; moving tokens to cookies alone is not a complete solution. Current localStorage tokens remain valid until expiry after local logout and are readable by scripts running in the origin.

## Tests, evidence, and repository quality

The passing suite is useful but very small for the feature set. It lacks cross-user authorization, ordinary UML aliases/visibility syntax, table semantics, missing-ID tracing, empty-input scoring, persistent-link scoring, frontend analysis progression, failed upload recovery, and concurrency coverage.

Some tests are weak or leak state: the parser test accepts broken table extraction; the traceability test comments out intended assertions and largely checks that a list is returned; analyzer tests globally replace parser/session behavior. Use fixtures and scoped monkeypatching so test order cannot hide integration failures.

The evaluation dataset has **33 requirement records**. `backend/scripts/evaluate.py` feeds pre-labelled dictionaries directly to the deterministic SRS rules and scores five rule IDs. It does not measure DOCX/PDF extraction, UML, traceability, LLM accuracy, repair preservation, or complete end-to-end quality. The reported 0.98 F1 should be described as a small deterministic-rule benchmark. Scoring sets by `(requirement_id, rule_id)` also collapses multiple cases with duplicate or missing IDs; use independent case IDs.

Add a held-out corpus with actual DOCX/PDF/table layouts, supported PlantUML variants, misleading lexical matches, conflicting requirements, and human-labelled repair judgments. Report per-stage precision/recall, extraction coverage, false-positive counts, failure rate, latency, cost, and confidence intervals where sample sizes support them.

CI should run meaningful API/integration and frontend workflow tests, migration checks, lint/type checks, and dependency scans. Use `npm ci` with the committed lockfile. Align supported Python/Node versions across local setup, CI, and containers, and pin test/dev dependencies.

Repository cleanup should remove obsolete patch scripts from normal maintenance paths, replace stale generated DOCX test artifacts with fixtures where needed, fix the demo seed script, and update the feasibility report's outdated model names and role/assignment descriptions. Add an `.env.example`, supported-format samples, reproducible demo instructions, contribution guidance, and a license if reuse is intended. The inspected GitHub issue and PR collections were empty; create a prioritized backlog rather than treating successful CI as the entire quality signal.

## Features worth adding, in order

| Feature | User value | Priority |
|---|---|---|
| Source-linked findings with highlighted evidence | Users can verify and locate each problem immediately. | First |
| Progress, partial-result states, retry/cancel | Users understand long or failed analyses and can recover. | First |
| Complete report with scores and evaluation coverage | Makes the existing analysis useful and honest. | First |
| Parsed-document preview and manual extraction correction | Stops parser errors from silently becoming quality judgments. | First |
| Accept/edit/reject rewrites with tracked diffs | Turns suggestions into a practical authoring workflow. | Next |
| Stable project revisions and change impact analysis | Shows changed requirements, affected diagrams, and resolved/new defects. | Next |
| Manual trace creation with confidence/evidence | Lets reviewers repair the inferred model. | Next |
| Custom rubric, lexicon, and template profiles | Supports different courses and organizational conventions. | Next |
| Teams, reviewer comments, assignments and role permissions | Makes sense if classroom/team review is the chosen product direction. | Later |
| DOCX/PDF report export and revised-document export | Supports sharing and submission without copy/paste. | Next |
| Local/private provider or deterministic-only operation | Supports private documents and unreliable connectivity. | Later |
| Semantic trace suggestions and test-case generation | Useful differentiators once correctness is measured. | Later |

## Recommended delivery sequence

**Release gate:** Fix cross-user access, vulnerable dependency pins, missing-ID crashes, fake rewrite verification, empty-input scoring, and the Docker API URL mismatch. Add regression tests proving the fixes.

**Complete one reliable workflow:** Create project -> upload valid artifacts -> inspect extraction -> run analysis with progress -> review source-linked findings and scores -> correct or reject suggestions -> create a revision -> compare -> export. Include expired sessions and failed-stage recovery.

**Harden the foundation:** Add immutable revisions/runs, atomic result publication, durable jobs when deployment needs them, safe artifact handling, database constraints, structured telemetry, and reproducible environments.

**Then differentiate:** Improve measured trace quality, custom rubrics, collaboration, document export, and change-impact/test generation. Preserve the modular monolith until actual scale or ownership boundaries justify additional services.

The best route to a much stronger project is to make every result explainable, every normal input safe to analyze, and the whole review loop usable. Additional AI features become valuable once users can trust the underlying evidence.
