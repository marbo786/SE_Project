#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
domain="${1:-}"
if [[ ! "$domain" =~ ^[a-zA-Z0-9][a-zA-Z0-9.-]+$ || "$domain" == *YOUR-NAME* ]]; then
  echo 'Usage: bash scripts/demo_up.sh your-assigned-domain.ngrok-free.app' >&2
  exit 1
fi
for command in docker ngrok curl; do
  command -v "$command" >/dev/null || { echo "Install $command first. See docs/DEMO.md." >&2; exit 1; }
done
if [[ ! -f backend/.env ]] || grep -q 'YOUR-PROJECT' backend/.env; then
  echo 'Prepare backend/.env with your Vercel URL using docs/DEMO.md.' >&2
  exit 1
fi
docker compose up -d --build postgres redis migrate backend worker dispatcher
ready=false
for ((attempt=0; attempt<30; attempt++)); do
  if curl --fail --silent --max-time 2 http://127.0.0.1:8001/ready >/dev/null; then
    ready=true
    break
  fi
  sleep 2
done
if [[ "$ready" != true ]]; then
  echo 'API not ready. Inspect docker compose logs backend migrate worker dispatcher.' >&2
  exit 1
fi
echo 'The tunnel exposes open signup. Keep this terminal open; Ctrl+C stops the tunnel.'
echo 'After the demo, run docker compose down from the repo root (without -v).'
exec ngrok http 8001 --url "https://$domain"
