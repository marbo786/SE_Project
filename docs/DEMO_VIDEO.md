# Record the 60-second localhost demo

Record seven separate clips in a 1920×1080 browser window at 125–150% zoom. Record voiceover separately and add captions in the editor. Stop recording while analysis runs; cut directly to the completed report. This is a demo of evidence and human review, not a claim of production readiness or AI accuracy.

## Prepare once before taking clips

1. Start `scripts/demo_local.ps1`; keep its terminal open. Run `demo/build_demo_srs.py`, then `demo/seed_demo.py --reset --with-compare` with `.venv313/Scripts/python.exe`. Wait for the printed report links.
2. Sign in before recording. Hide bookmarks, close unrelated tabs and notifications, and use only synthetic documents. Keep terminals, passwords and real accounts out of the recording. The sidebar shows the fictional demo email: crop or mask that account strip in the editor if no email should appear on screen.
3. Set browser zoom to 125% first; use 150% only if the chosen detail still fits. Prefer dark theme and comfortable spacing. Keep the viewport 16:9. The capture script emulates the layout of 125% zoom with a 1536×864 CSS viewport at 1.25 device scale, producing 1920×1080 PNGs; manually check the actual browser chrome and native zoom before recording.
4. Keep one tab on the seeded v1 report, another on the seeded v2 comparison, and one on **New project** for the fresh **Library Lending** project. Use the URLs printed by seed. Reopen these URLs to reset navigation without rerunning analysis.
5. Check `.demo-runtime/seed.json` only off camera if you need the run IDs. `demo/screenshots/` contains clip references after `node demo/capture_demo.mjs` completes. That script creates a separate fresh **Library Lending** project and exercises the mutations as well as taking screenshots.

## Seven clips and timing

| Clip | Time | Project and exact click path | Pause on |
|---|---:|---|---|
| A | 10s | Fresh **Library Lending**: **New project** → **Specification Name** → **What should this review cover?** = **Requirements and architecture (all three UML diagrams)** → check **Include AI suggestions using the configured provider. Deterministic checks work offline.** → **Continue to Document Upload** → choose `demo/library-srs-v1.docx` → **Continue to UML Diagrams**. Select **Use Case Diagram**, **Class Diagram**, **Sequence Diagram** in turn, choose each matching file, and click **Add Model** each time. **Review files and scope** → **Save draft and review extraction** → **Extract requirements**. | The extraction preview with correct functional classifications. Cut out file-picker repetition; all four files must still be attached. |
| B | 6s | Fresh project: check **I have reviewed the extracted content and am ready to analyze this revision.** → **Analyze this revision**. Stop capture during the wait. Resume on the completed report, or use the seeded v1 report. | **Quality score**, scope/category contributions and status. Do not dwell on the mock usage counters. |
| C | 7s | Seeded v1 or fresh completed v1: **Findings** → **Search findings** = `FR-401` → **View source for NFR-1**. | **Source evidence**, the “respond fast” quote and recorded paragraph location. |
| D | 6s | Same v1 report: **Search findings** = `FR-606` → **View source for FR-606**. | `isBookAvailable()` and the explanation that its argument count does not match receiver **Catalog**. The class defines one parameter; the deliberate sequence supplies none. |
| E | 8s | V1: **Traceability Matrix**. For the second half use seeded v2: **Compare revisions** → **Compare the selected report with** = v1 → scroll to **Architecture impact paths**. | Trace candidates and a changed-requirement path. Say “possible impact” for suggested links; they are not confirmed proof. |
| F | 8s | V1: **Findings** → search `FR-401`. Show **Accept finding** / **Dismiss finding** and **Review note**. In **Review rewrite suggestion**, show **Proposed requirement**, edit it, check **I reviewed the intent, thresholds, conditions and exceptions. Apply only to a draft.**, then **Apply to draft**; **Reject suggestion** is the alternative. | The human confirmation and draft-only action. **Accept finding** accepts the finding, not the AI rewrite. Mock rewrites intentionally repeat the source and remain **REVIEW REQUIRED**. Explain that the reviewer supplies the correction. |
| G | 15s | Fresh project: **Edit a new draft**. In **Source documents**, set **Document type** = **Sequence diagram**, **Add or replace** = **Replace library_sequence.puml**, choose `library_sequence_fixed.puml`, and click **Save source file**. **Extract requirements**, then make the three edits below using **Save requirement** for each. Confirm and **Analyze this revision**. Cut the wait. On the new report, **Compare revisions** → choose v1. | The changed requirements and **Resolved Defects** including `FR-401`, `FR-402`, `FR-411` and `FR-606`. Use the pre-seeded comparison for the final held shot if needed. |

Total: 60 seconds. Do not try to perform every upload, edit and analysis in one uninterrupted take.

## Clip G edits and the order that matters

Replacing any source file clears extraction corrections in that draft. **Replace the sequence first, extract again, then edit requirements.** If clip F already applied an edit to the draft, reapply it after replacement. This is existing app behavior, not hidden by the seed or capture scripts.

Use the following corrected text (also present in `library-srs-v2.docx`):

- FR-5: `FR-5 The Catalog shall return search catalog titles with identifiers.`
- NFR-1: `NFR-1 The Catalog shall respond to search requests within 2 seconds for 20 concurrent users.`
- NFR-2: `NFR-2 The Catalog shall maintain service uptime of 99% per calendar month.`

The 2-second, 20-user and 99% targets are demo assumptions, not tool recommendations. The v2 DOCX is the corrected source reference. For the video, edit the existing extracted requirements instead of replacing the whole SRS: this preserves requirement identity, so Compare shows three **changed** requirements and can display impact paths. Whole-document replacement can appear as added/deleted requirements instead.

The seeder follows this same sequence through HTTP: retain the v1 SRS, replace the diagram, extract, apply the v2 text through requirement correction endpoints, and analyze. It does not write database rows directly.

## Reset and re-record without waiting on camera

- A: create another fresh **Library Lending** project; no seed reset needed.
- B–E: reopen the printed v1 or comparison URL. Reports are immutable; changing tabs and filters does not change them.
- F: **Reset review** resets a finding decision. Rejecting a suggestion leaves its editing controls visible. Applying a suggestion hides them behind the saved decision; for a pristine F take, use a fresh v1 project or run seed with `--reset --with-compare` off camera.
- G: the pre-seeded v2 comparison provides the ending without waiting. Record the draft actions against the fresh project. For another clean draft take, start from a fresh v1 project; do not accumulate extra analyses in the same project indefinitely.
- `--reset` removes only the demo account's projects from normal views; deletion is the app's normal soft deletion. Repeated seeding without reset is idempotent. Normal per-user analysis and authentication limits remain active; plan a few takes rather than resetting in a tight loop.

## Known on-screen limits

- The original dashboard sample in `frontend/public/Sample_Requirement/` is a smaller legacy walkthrough. For this recording use the richer files under `demo/`.
- Lexical trace suggestions can leave trace-gap findings even when the deliberate SRS and sequence defects are fixed. Show the specific resolved defects, not a claim that v2 is perfect or all paths are confirmed.
- AI usage, coverage and review panels are verbose. Mock coverage means the scripted provider returned every expected item; it is not actual model review. Scores are scoped tool output, not validated quality metrics.
- Numeric thresholds are your demo assumptions. No rewrite is automatically approved; **Apply to draft** requires your confirmation.
- Source replacement discards draft extraction corrections; the order above avoids losing visible edits. New drafts preserve old reports.
- Use **Traceability CSV** to download a matrix if desired, but keep file-save dialogs out of the 60-second cut.
- Existing parser/scoring limitations and any remaining trace gaps are left intact. No analysis rule or score weight is tuned for the video.

## Verified recording result

The localhost Playwright walkthrough produced eight 1920×1080 reference screenshots (A–G, with separate trace-matrix and impact-path shots). V1 had eight findings; v2 had two remaining trace gaps, six resolved findings, zero new findings and three changed requirements. The deliberate sequence mismatch was resolved. Trace CSV download was checked against the report's trace links.

The three supplied diagrams were retained; the deliberate mismatch variant differs from the corrected sequence only by removing the `bookId` argument. Both DOCX files extract nine requirements with all expected sections and no parser warnings; all four diagrams parse without warnings.

PowerShell startup, HTTP-only reset/seeding and repeated idempotent seeding were exercised on Windows. Backend tests: 149 passed, one PostgreSQL-only test skipped because no test PostgreSQL URL was configured. Frontend build and all eight browser tests passed. Bash startup received a syntax check only. DOCX page rendering could not be checked because LibreOffice is unavailable; document extraction and checks were verified with the app itself.
