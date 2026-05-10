#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ $# -gt 0 ]]; then
  echo "[dev-up] This script does not support runtime-specific arguments."
  echo "[dev-up] Configure .env, then run ./scripts/dev-up.sh"
  exit 1
fi

verify_default_users() {
  local user_count

  user_count="$(
    docker compose exec -T postgres psql -U app -d multimodal_mvp -tAc \
      "SELECT count(*) FROM users WHERE username IN ('admin', 'curator', 'analyst', 'user');" |
      tr -d '[:space:]'
  )"

  if [[ "$user_count" != "4" ]]; then
    echo "[dev-up] ERROR: Default users were not initialized correctly. Found ${user_count:-0}/4 users."
    echo "[dev-up] Try running: docker compose --profile tools run --rm --build migrate python -m scripts.init_db"
    exit 1
  fi
}

echo "[dev-up] Starting core services..."
docker compose up -d postgres qdrant

echo "[dev-up] Applying database migrations..."
docker compose --profile tools run --rm --build migrate

echo "[dev-up] Ensuring default users..."
docker compose --profile tools run --rm --build migrate python -m scripts.init_db

echo "[dev-up] Verifying default users..."
verify_default_users

echo "[dev-up] Starting api and frontend..."
docker compose up -d --build --force-recreate api frontend

echo
echo "[dev-up] Done."
echo "Frontend: http://127.0.0.1:8080"
echo "API: http://127.0.0.1:8000"
echo "Health: http://127.0.0.1:8000/health"
echo
echo "OpenCode generation requires an API key (keep it out of .env):"
echo "  OPENCODE_API_KEY='sk-...' ./scripts/dev-up.sh"
echo "  # or runtime override: OPENCODE_API_KEY_RUNTIME='sk-...' ./scripts/dev-up.sh"
echo "Verify generation is configured:"
echo "  curl -fsS http://127.0.0.1:8000/health | python -m json.tool | grep configured"
