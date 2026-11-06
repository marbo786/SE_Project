# Development and verification

Use Python 3.13 and Node 24. On Windows, `./run_backend.ps1` creates `.venv313`, installs the pinned dependencies, migrates the database, and starts the API on 127.0.0.1:8000. Copy `backend/.env.example` to `backend/.env` for a fresh installation; preserve any existing configuration. Install frontend dependencies with `npm ci` from `frontend`, then run `npm run dev`.

The browser calls relative `/api` URLs. Vite forwards them to `http://127.0.0.1:8000` locally or the `API_PROXY_TARGET` environment variable. Development Compose sets that target to `http://backend:8000`; backend host port 8001 is for direct API debugging. `docker compose up --build` starts the development stack. Production serving and durable jobs are separate release milestones.

Migrations are explicit: run `python -m alembic upgrade head` from `backend` before starting the API. Importing the application no longer changes the schema or marks another process's analysis as failed. `/health` checks the process; `/ready` checks database connectivity and the security schema. Back up existing databases before applying migrations. The additive security migration preserves accounts and password hashes; old login tokens expire immediately, and users sign in again. Successful login upgrades legacy bcrypt hashes to Argon2id.

Browser sessions use HttpOnly cookies and a CSRF header. Authentication state comes from `/auth/me`; localStorage credentials are removed. API clients can still use the returned opaque bearer token, which logout and password reset revoke. Production requires `APP_ENV=production`, `COOKIE_SECURE=true`, an HTTPS `PUBLIC_URL`, and SMTP configuration. Use an explicit trusted CORS origin. Password-reset and verification messages are written to ignored `.eml` files in `MAIL_SINK_DIR` during local development; open the link in the message. These files contain temporary credentials and must not be shared.

Run `./scripts/check.ps1`, or `.venv313/Scripts/python.exe -m pytest backend/tests -q` then `npm run build` from `frontend`. Run `.venv313/Scripts/python.exe scripts/check_http_local.py` to start disposable API/Vite processes and check signup, cookies, CSRF, upload, and logout through the real proxy. It uses ports 18003 and 15173, synthetic accounts, temporary storage, and automatic cleanup. CI also checks the Compose flow, Python/npm advisories, and repository secret leakage.

Tests override database, upload directory, provider, and mail settings before importing application modules. SQLite tests enforce foreign keys. Tests never use the user's existing database. Windows asyncio and subprocesses need local socket/process permissions; sandbox restrictions can fail infrastructure independently of application behavior. Strict expected failures track analysis defects awaiting their milestones; they are not successful acceptance tests.

Uploads: 10 MB compressed, 50 MB expanded DOCX, at most 1,000 ZIP entries, 100 PDF pages, and 1,000,000 extracted characters. A dedicated parser subprocess has a 20-second timeout and a 512 MB address-space limit on Linux. Native Windows enforces the timeout and input limits; use Linux containers for a hard parser memory ceiling. Development Compose additionally caps API memory at 1 GB. Limits are configurable operating defaults, not measured capacity guarantees. Image-only/encrypted/corrupt files and unsafe PlantUML preprocessing are rejected. Draft replacement preserves the prior file on validation failure; inputs lock when analysis starts.

M6 adds rendered desktop/mobile screenshots, keyboard/focus checks, text-resize checks, and automated accessibility scans. Manual screen-reader review and broader usability qualification remain M8 gates. See [the workspace guide](REVIEW_WORKSPACE.md) and [historical implementation status](archive/IMPLEMENTATION_STATUS.md) for evidence and limitations.
# Revision and history checks

The [revision guide](REVISION_HISTORY.md) covers contracts, backup rehearsal, cutover, and retention. Browser checks use isolated services and data:

```powershell
cd frontend
npm ci
npx playwright install chromium
cd ..
.\.venv313\Scripts\python.exe scripts/check_http_local.py --browser
```

Screenshots and failed-test traces are written under `frontend/test-results` (ignored). PostgreSQL checks run in CI; to run them locally, point `TEST_POSTGRES_URL` at a disposable PostgreSQL database. The test creates and removes a unique schema, not the database.
