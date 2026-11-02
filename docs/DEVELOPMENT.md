# Development and verification

Install backend tools with `python -m pip install -r backend/requirements-dev.txt` in a virtual environment. Install frontend dependencies with `npm ci` from `frontend`. Run `./scripts/check.ps1` from PowerShell, or `python -m pytest -q` from `backend` followed by `npm run build` from `frontend`.

Tests override database, upload directory, provider, and secret settings before importing application modules. Fixtures restore dependency overrides and monkeypatches. Test data never uses the existing application database. On Windows, asyncio requires permission to create local socket pairs; a restricted sandbox can block test setup independently of application behavior.

The initial baseline has 11 passing tests and nine strict expected failures reproducing known audit issues. An expected failure is an unresolved bug, not a passed acceptance check. Each fix removes its expected-failure marker. CI runs on the improvement branch as well as main.

Supported input scope under development: DOCX paragraphs and requirement tables, text-based PDFs, and PlantUML use-case/class/sequence diagrams. Image-only PDFs and unsupported diagram syntax must be reported rather than graded as valid input. Upload limit: 10 MB. Decompressed size, page/element bounds, and parser time limits are introduced with upload hardening.

Rendered visual/accessibility baseline is pending: earlier browser tooling could not reach the local development service. UI changes must still undergo supported browser review before M6/M8 sign-off. The original audit's visual ratings are provisional.
