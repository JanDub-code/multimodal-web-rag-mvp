#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ $# -gt 0 ]]; then
  echo "[dev-up] This script no longer supports Ollama-specific arguments."
  echo "[dev-up] Start LM Studio separately and run ./scripts/dev-up.sh"
  exit 1
fi

export DOCKER_LLM_BASE_URL="${DOCKER_LLM_BASE_URL:-http://host.docker.internal:1234/v1}"

echo "[dev-up] Starting core services..."
docker compose up -d postgres qdrant

echo "[dev-up] Applying database migrations..."
docker compose --profile tools run --rm migrate

echo "[dev-up] Ensuring default users..."
docker compose run --rm api python -m scripts.init_db

echo "[dev-up] Starting api and frontend..."
docker compose up -d api frontend

echo
echo "[dev-up] Done."
echo "Frontend: http://127.0.0.1:8080"
echo "API: http://127.0.0.1:8000"
echo "Health: http://127.0.0.1:8000/health"
echo "LLM base URL for containers: ${DOCKER_LLM_BASE_URL}"
echo
echo "Make sure LM Studio server is running and the configured model is loaded."
