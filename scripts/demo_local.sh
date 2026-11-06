#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
python="$repo_root/.venv313/bin/python"
if [[ ! -x "$python" ]]; then echo 'Install dependencies in .venv313 first. See docs/DEMO.md.' >&2; exit 1; fi
[[ -f frontend/node_modules/vite/bin/vite.js ]] || { echo 'Run npm ci in frontend first.' >&2; exit 1; }
"$python" -c 'import socket; sockets=[socket.socket() for _ in range(2)]; [s.bind(("127.0.0.1",p)) for s,p in zip(sockets,[8001,5174])]'
mkdir -p .demo-runtime
export APP_ENV=development COOKIE_SECURE=false LLM_PROVIDER=mock JOB_BACKEND=local SMTP_HOST='' GROQ_API_KEY=''
export PUBLIC_URL=http://localhost:5174 CORS_ORIGINS=http://localhost:5174,http://127.0.0.1:5174
export DATABASE_URL="sqlite:///$repo_root/.demo-runtime/demo.db" UPLOAD_DIR="$repo_root/.demo-runtime/uploads" MAIL_SINK_DIR="$repo_root/.demo-runtime/mail"
export API_PROXY_TARGET=http://127.0.0.1:8001 LLM_PRICING='{"mock/mock-model-v2":{"input":0,"output":0}}' LLM_RUN_COST_BUDGET_MICROUSD=1000000
(cd backend && "$python" -m alembic upgrade head)
pids=()
cleanup() { for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null || true; done; wait || true; }
trap cleanup EXIT
trap 'exit 130' INT TERM
(cd backend && exec "$python" -m uvicorn app.main:app --host 127.0.0.1 --port 8001) >.demo-runtime/api.log 2>&1 & pids+=("$!")
(cd backend && exec "$python" -m app.jobs.worker) >.demo-runtime/worker.log 2>&1 & pids+=("$!")
(cd frontend && exec node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5174 --strictPort) >.demo-runtime/frontend.log 2>&1 & pids+=("$!")
ready=false
for ((attempt=0; attempt<45; attempt++)); do
  for pid in "${pids[@]}"; do kill -0 "$pid" 2>/dev/null || { echo 'Demo process stopped; see .demo-runtime logs.' >&2; exit 1; }; done
  if curl --fail --silent --max-time 2 http://127.0.0.1:5174/api/ready >/dev/null; then ready=true; break; fi
  sleep 1
done
[[ "$ready" == true ]] || { echo 'Demo did not become ready.' >&2; exit 1; }
echo 'Demo ready: http://localhost:5174'
echo 'Keep this terminal open. Ctrl+C stops the demo; data stays in .demo-runtime.'
wait -n "${pids[@]}"
