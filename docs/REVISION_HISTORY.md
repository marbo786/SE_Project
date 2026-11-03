# Revisions, reports, and retention

Projects now have stable IDs. Two projects with the same name are independent. Create a draft inside an existing project when revising its documents; naming a new project the same thing does not create a revision.

## Browser workflow

1. Create a project and upload its sources. A failed upload can be retried on the same saved project.
2. In the draft, add or explicitly replace sources. Multiple diagrams of the same type are supported (20 total files, including one SRS).
3. Extract and review requirements. Correct text, authored IDs, classification, or quality category. Original text, source spans and source downloads remain available.
4. Confirm the extraction and analyze. Starting seals the revision. Further edits require another draft.
5. Use the report's history selector to inspect earlier attempts. Choose two reports in Version Diff to compare them. The last complete report remains published if a subsequent attempt is partial or fails.

The first browser checkpoint retains the existing visual language: graphite `#17181B` inputs, charcoal `#1D1E22` source panel, light `#E7E7E9` text, readable secondary `#B9BBC3`, blue `#A7C4E4` links and focus, `#51535c` input boundaries. System sans text and left alignment prioritize source reading. The draft separates the source-file list from occurrence-level editing; original text sits beside each correction. Full navigation/accessibility redesign remains M6.

## Contracts and invariants

Browser `/api/v1` is proxied to backend `/v1`. Legacy routes remain adapters until the full workspace migration is complete.

| Command/read | Route |
|---|---|
| Create/list projects | `POST/GET /v1/projects` |
| Create or resume one open draft | `POST /v1/projects/{id}/drafts` |
| Revision list/details/options | `/v1/projects/{id}/revisions[/{revision_id}]` |
| Add or explicitly replace a source | `POST .../revisions/{revision_id}/artifacts` |
| Delete a draft source | `DELETE .../artifacts/{artifact_id}` |
| Extract/read canonical input | `POST/GET .../revisions/{revision_id}/extraction` |
| Correct a requirement occurrence | `PATCH .../revisions/{revision_id}/requirements/{element_key}` |
| Start analysis | `POST .../revisions/{revision_id}/runs` → `202` |
| Status/report/findings | `/v1/runs/{id}`, `/report`, `/findings` |
| Compare with another run in the same project | `/v1/runs/{id}/compare/{previous_id}` |
| Append a review decision | `POST /v1/runs/{id}/decisions` |
| Export selected run's reviewed trace links | `/v1/runs/{id}/traceability.csv` |
| Archive, restore, or request deletion | `POST /v1/projects/{id}/lifecycle` |

Draft mutations and run creation require `If-Match: <edit_version>` (`428` if missing, `409` for a stale or sealed draft). Pass `Idempotency-Key` on project/draft creation, upload finalization, and analysis creation. Identical retries return the original accepted response; a reused key with different input returns `409`. Keys should be unique per intended command and retained until it succeeds. A retry response may still say `queued`; use the status endpoint for current state.

Run manifests include file hashes, effective corrections, analysis scope and frozen rule configuration. Stored file changes outside the application are rejected. Normalized run findings, trace candidates, scores and report snapshots are never replaced by subsequent analyses. Legacy tables are only compatibility projections.

Review decisions are append-only and separate from machine scores. A decision includes the previous decision ID for optimistic concurrency. Only identical effective inputs and compatible versions carry decisions to new runs; changed input makes prior review context stale. Legacy decisions have unknown original reviewers, explicitly recorded as such.

Comparisons preserve multiplicity: several missing sections or repeated conflicts do not collapse into one record. Explicit correction lineage permits changed-requirement comparisons. Replacing an entire source starts new lineage; the system does not guess identity from matching `FR-1` labels. Rubric/profile/mode/config differences are disclosed as non-comparable scores.

## Retention

Archiving hides a project from the active list and makes it read-only. Restore re-enables editing. Deletion requires the exact project name, hides all project resources, and allows restoration for 30 days. Maintenance permanently removes expired soft deletions only when explicitly applied:

```powershell
.\.venv313\Scripts\python.exe backend/scripts/purge_deleted.py
.\.venv313\Scripts\python.exe backend/scripts/purge_deleted.py --apply
```

The default is a dry run. Review a backup before applying it. Purging removes dependent project records and checks all surviving artifact references before unlinking a file directly inside the configured upload root. It does not recursively delete directories or follow external file paths. Minimal purge audit events remain. No real project was purged during implementation.

## Migration and recovery

Stop application/worker writes before backing up database and files together. SQLite backup uses the backup API; copied documents and database are hashed. Backups contain sensitive data and are ignored by Git.

```powershell
.\.venv313\Scripts\python.exe backend/scripts/backup_rehearsal.py snapshot --database backend/srs_reviewer.db --uploads backend/uploads --destination backups/before-history
.\.venv313\Scripts\python.exe backend/scripts/backup_rehearsal.py rehearse --backup backups/before-history --destination backups/history-rehearsal
```

Rehearsal restores into a new directory, maps restored file paths, upgrades only that copy, reconciles user records, ownership, original findings, table counts, and foreign keys. Missing files are reported; a successful schema migration does not reconstruct an unavailable source.

The additive migration gives each legacy project its own revision 1, retaining original version labels as `legacy_version`. Existing reports are imported unchanged as legacy runs with unknown parser/rules/rubric provenance. No name-based merging occurs. An interrupted legacy analysis becomes a failed legacy attempt with an explanation. Old tables and original files remain available.

After reviewing reconciliation, apply `alembic upgrade head` under the write freeze, verify readiness and report access, then reopen writes. Prefer forward repairs. A schema downgrade removes the new history tables; it is not a data restore. If restoring a pre-cutover backup, account for every write since that backup before switching over. PostgreSQL deployments should take `pg_dump` plus the matching private upload volume under the same write freeze; SQLite's backup utility is deliberately not a PostgreSQL backup tool.

## Verification at the M3 checkpoint

- Disposable populated migrations cover colliding names, legacy findings/decisions, upgrade/downgrade, restoration and file hashes.
- SQLite concurrent draft creation produces one draft and a single monotonically allocated revision number. A PostgreSQL 16 CI job exercises the same migration and concurrency behavior.
- Real Chromium workflow covers correction → confirmation → analysis → new draft → unchanged prior report, plus a 390 px viewport and screenshots.
- On 2026-11-04, a rehearsal on copies of the local backend database preserved 2 users, 12 projects, 22 documents, 150 findings, 12 scores, and ownership. All 22 source files were found and copied. The empty root database was rehearsed separately. Originals were not migrated by this rehearsal.

Long-running jobs still use the compatibility background-task dispatch at this checkpoint. M4 replaces it with durable outbox/worker execution. AI validation, generated API types, complete accessible review interactions, collaboration and release qualification remain in the accepted milestone plan.
