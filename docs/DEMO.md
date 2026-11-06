# Short demo: Vercel frontend and laptop backend

This is a temporary demonstration, not a production deployment. Vercel serves the static Vite build. Its `/api/:path*` rewrite strips `/api` and forwards to the laptop's ngrok static domain. Docker runs PostgreSQL, Redis, migrations, the API, a Celery worker and the dispatcher. There is no frontend container in this demo.

## 1. Prepare the accounts and URLs

Install Docker with Compose v2 and the ngrok CLI on the laptop. Start Docker. Install Node 24 for local builds. Sign in to ngrok, find your assigned free static domain, and authenticate the CLI once:

```sh
ngrok config add-authtoken YOUR_NGROK_TOKEN
```

Keep the token out of Git. Use the domain actually assigned to your account, not an invented subdomain. The examples below use `YOUR-NAME.ngrok-free.app` and `YOUR-PROJECT.vercel.app` as placeholders.

Import the repository into Vercel, choose the **Vite** preset, set **Root Directory** to `frontend`, **Build Command** to `npm run build`, and **Output Directory** to `dist`. Select the `demo-finalize` branch for the demo deployment (or deploy that local checkout with the Vercel CLI); do not merge into main just to deploy. Use one stable Vercel project URL throughout these steps, rather than a changing preview URL.

Edit `frontend/vercel.json`: replace `https://YOUR-NAME.ngrok-free.app` with the assigned tunnel URL. Keep the API rewrite first and the `/index.html` SPA fallback second. The backend routes do not have an `/api` prefix. Leave `VITE_API_URL` unset in Vercel so the client continues to use relative `/api` requests. Redeploy after changing the rewrite. Static assets and the sample files remain served by Vercel. See [Vercel's external rewrite documentation](https://vercel.com/docs/routing/rewrites).

## 2. Configure the laptop backend

From the repository root, copy the demo example only if `backend/.env` does not already exist:

```powershell
# PowerShell
if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.demo.example backend/.env }
```

```sh
# Bash
test -f backend/.env || cp backend/.env.demo.example backend/.env
```

If the file already exists, edit its settings to match the example; the scripts will not overwrite it. Set both `PUBLIC_URL` and `CORS_ORIGINS` to the exact HTTPS Vercel URL, with no trailing slash. Keep:

```dotenv
APP_ENV=development
COOKIE_SECURE=true
PUBLIC_URL=https://YOUR-PROJECT.vercel.app
CORS_ORIGINS=https://YOUR-PROJECT.vercel.app
LLM_PROVIDER=mock
```

Development mode is intentional: it allows the mock provider and does not require SMTP. The production startup guards remain unchanged. Vercel forwards API responses, including the host-only cookies, back through the browser's own origin; the existing CSRF header and origin checks remain in use. Sign in through Vercel, not directly through local HTTP, because the demo's cookies are Secure. Do not use `*` for the origin or switch the frontend to direct cross-origin tunnel calls.

## 3. Start the demo

From the repository root:

```powershell
.\scripts\demo_up.ps1 -Domain YOUR-NAME.ngrok-free.app
```

or:

```sh
bash scripts/demo_up.sh YOUR-NAME.ngrok-free.app
```

Both scripts run the following Compose subset, wait for the existing `/ready` endpoint, and start ngrok in the foreground:

```sh
docker compose up -d --build postgres redis migrate backend worker dispatcher
ngrok http 8001 --url https://YOUR-NAME.ngrok-free.app
```

The API is bound to `127.0.0.1:8001`; no frontend container is started. If a frontend container remains from an earlier local session, stop it with `docker compose stop frontend`. Migrations must finish successfully. In a second terminal, check:

```sh
docker compose ps -a
docker compose logs --tail=80 migrate backend worker dispatcher
curl --fail https://YOUR-PROJECT.vercel.app/api/ready
```

PowerShell users can use `Invoke-RestMethod https://YOUR-PROJECT.vercel.app/api/ready`. Expect `{"status":"ready"}`. A 502/tunnel-offline response means Docker/ngrok is unavailable or the rewrite points at the wrong domain. HTML instead of JSON usually means the rewrite is wrong or an ngrok browser warning was returned. ngrok documents its [free-tier browser warning and API behavior](https://ngrok.com/docs/pricing-limits/free-plan-limits); check the Network response before changing app configuration. A 403 on mutation usually means `PUBLIC_URL`/`CORS_ORIGINS` does not match the URL in the address bar. After changing `backend/.env`, rerun the Compose command to recreate the services.

## 4. Walk through the project

1. Open the Vercel site, register a demo-only account, log out, then sign in with it. Registration and login do **not** require email verification; no seed script or SMTP setup is necessary. Avoid password recovery during this demo: development recovery mail is written locally rather than delivered to an inbox.
2. Expand **Try a sample review** on the dashboard. Download the library DOCX from `Sample_Requirement/`.
3. Choose **New project**, name it, select **Requirements only**, and leave AI suggestions unchecked for the shortest deterministic walkthrough. Upload the DOCX, continue past the optional UML step, then **Save draft and review extraction**.
4. Select **Extract requirements**, inspect the source text, check the confirmation box, and select **Analyze this revision**. Wait for the report; show findings, evidence and the scoped score.
5. Select **Edit a new draft**, change the ambiguous “respond fast” requirement to an explicitly explained demo target, save it, confirm the extraction, and analyze again. In **Compare revisions**, select the earlier report and show the changed requirement. Any target you introduce is a demonstration assumption, not a tool recommendation.
6. Download **Traceability CSV**. Requirements-only reviews can have a header-only matrix because there are no UML targets. For populated trace candidates, use **Requirements and architecture** and attach the supplied `library_usecase.puml`, `library_class.puml` and `library_sequence_fixed.puml` with their corresponding diagram types, then analyze and download the CSV.
7. To demonstrate the optional provider path, select **Include AI suggestions** at creation or **Deterministic and AI checks** in the draft. With `LLM_PROVIDER=mock`, outputs are scripted fixtures, not model judgments. Do not present mock scores, conflict coverage or suggestions as evidence of real AI accuracy.

Optional Groq: use `LLM_PROVIDER=groq`, your own `GROQ_API_KEY`, an available `LLM_MODEL`, and verified `LLM_PRICING` entries as described in [AI_SAFETY.md](AI_SAFETY.md), then recreate backend/worker/dispatcher. This is optional and uses an external service; the default walkthrough needs no API key.

## 5. Stop immediately after the demo

Press **Ctrl+C** in the script/ngrok terminal to close the public tunnel. The containers keep running until you stop them:

```sh
docker compose down
```

Do not add `-v`: the named volumes hold demo accounts, documents and reports. The Vercel static page may still load after shutdown, but API calls will fail; remove/disable the Vercel deployment if you no longer want the page public.

The laptop must remain powered on, awake and online for the whole session. The free ngrok plan currently allows **1 GB outbound data and 20,000 HTTP requests per month**; report polling and file downloads count. Check the [official free-plan limits](https://ngrok.com/docs/pricing-limits/free-plan-limits) and your account usage before presenting. The tunnel exposes open signup and the API to anyone who knows the URL, so use synthetic data and shut the tunnel down afterward.

## Local verification

With backend development dependencies, frontend dependencies and Playwright Chromium installed:

```sh
python -m pytest backend/tests -q
npm --prefix frontend run build
python scripts/check_http_local.py --browser
```

The browser runner uses disposable SQLite, storage, a local worker and an HTTP Vite proxy with test cookies. It verifies the local journey; it does not verify the live Vercel/ngrok HTTPS hop or the laptop's PostgreSQL/Celery deployment. Check those separately before presenting.
