#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ $# -gt 0 ]]; then
  echo "[dev-up] This script does not support runtime-specific arguments."
  echo "[dev-up] Start LM Studio and Ollama separately, then run ./scripts/dev-up.sh"
  exit 1
fi

export DOCKER_LLM_BASE_URL="${DOCKER_LLM_BASE_URL:-http://host.docker.internal:1234/v1}"
export DOCKER_EMBEDDING_BASE_URL="${DOCKER_EMBEDDING_BASE_URL:-http://host.docker.internal:11434}"

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
echo "Embedding base URL for containers: ${DOCKER_EMBEDDING_BASE_URL}"
echo
echo "Make sure LM Studio and Ollama are running and the configured models are loaded."
