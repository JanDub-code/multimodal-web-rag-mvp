#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

WITH_OLLAMA="${1:-}"

if [[ "$WITH_OLLAMA" == "--with-ollama" ]]; then
  export DOCKER_OLLAMA_URL="${DOCKER_OLLAMA_URL:-http://ollama:11434}"
  echo "[dev-up] Starting core services with ollama profile..."
  docker compose --profile ollama up -d postgres qdrant ollama
else
  export DOCKER_OLLAMA_URL="${DOCKER_OLLAMA_URL:-http://host.docker.internal:11434}"
  echo "[dev-up] Starting core services..."
  docker compose up -d postgres qdrant
fi

echo "[dev-up] Applying database migrations..."
docker compose --profile tools run --rm migrate

echo "[dev-up] Ensuring default users..."
docker compose run --rm api python -m scripts.init_db

if [[ "$WITH_OLLAMA" == "--with-ollama" ]]; then
  docker compose --profile ollama up -d api
else
  docker compose up -d api
fi

echo
echo "[dev-up] Done."
echo "API: http://127.0.0.1:8000"
echo "Health: http://127.0.0.1:8000/health"
echo
echo "Use '--with-ollama' to run local ollama container profile."
