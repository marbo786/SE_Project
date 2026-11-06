# Local recording quickstart

This demo runs only on the laptop: Vite, FastAPI, SQLite and a local worker. It uses `APP_ENV=development`, `COOKIE_SECURE=false` and scripted mock responses. Existing databases, uploads and `backend/.env` are left alone; demo data lives in ignored `.demo-runtime/`. No Docker, tunnel, Vercel, SMTP or API key is needed.

Install Python 3.13, Node 24 and the existing pinned dependencies once:

```powershell
py -3.13 -m venv .venv313
.\.venv313\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
npm --prefix frontend ci
```

Skip environment creation if `.venv313` already exists. From the repo root, start the demo and leave the terminal open:

```powershell
.\scripts\demo_local.ps1
```

In a second terminal:

```powershell
.\.venv313\Scripts\python.exe demo/build_demo_srs.py
.\.venv313\Scripts\python.exe demo/seed_demo.py --reset --with-compare
```

Open **http://localhost:5174**. Sign in before recording with `demo-reviewer@example.com` / `Library-demo-only-2026!` (fictional local-only credentials). The script prints direct links to **Library Lending (ready)** and its comparison. Repeating seed without `--reset` reuses these records. `--reset` soft-deletes only this demo account's projects through the API and creates a fresh v1; add `--with-compare` to prepare v2 too. Other users' projects are untouched. Avoid resetting more than a few times per hour because normal app rate limits remain active.

For Bash on Linux/macOS, create `.venv313` with `python3.13 -m venv .venv313`, install the same requirements with `.venv313/bin/python -m pip`, run `bash scripts/demo_local.sh`, then use `.venv313/bin/python` for the two Python commands above. Bash also needs `curl`.

Use the [60-second recording guide](DEMO_VIDEO.md) for clips A–G, exact controls and reset choices. The DOCX files and diagrams are in `demo/`. Numeric targets in v2 are demo assumptions, not tool recommendations. Mock output demonstrates the review workflow, not real AI judgment or accuracy.

**Stop:** press Ctrl+C in the startup terminal. Data remains for the next take. Startup refuses occupied ports instead of stopping other programs; it uses frontend 5174 and API 8001. Logs are in `.demo-runtime/`. The [previous Vercel/ngrok guide](DEMO_VERCEL.md) is retained only as an alternative; it is not this recording setup.

For clip screenshots, install Chromium once with `cd frontend; npx playwright install chromium; cd ..`, then run `node demo/capture_demo.mjs` while the local stack is up. It creates a fresh **Library Lending** project and saves 1920×1080 screenshots to ignored `demo/screenshots/`.
