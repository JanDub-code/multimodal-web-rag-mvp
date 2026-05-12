#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
ENV_FILE="$ROOT_DIR/.azure-deploy.env"

_EXTERNAL_RESOURCE_GROUP="${RESOURCE_GROUP-}"
_EXTERNAL_PREFIX="${PREFIX-}"
_EXTERNAL_ACR_NAME="${ACR_NAME-}"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

[[ -n "$_EXTERNAL_RESOURCE_GROUP" ]] && RESOURCE_GROUP="$_EXTERNAL_RESOURCE_GROUP"
[[ -n "$_EXTERNAL_PREFIX" ]] && PREFIX="$_EXTERNAL_PREFIX"
[[ -n "$_EXTERNAL_ACR_NAME" ]] && ACR_NAME="$_EXTERNAL_ACR_NAME"

RESOURCE_GROUP="${RESOURCE_GROUP:-rg-xdub-2220}"
PREFIX="${PREFIX:-xdubrag}"
ACR_NAME="${ACR_NAME:?Set ACR_NAME or source .azure-deploy.env first.}"
ACR_BUILD_MODE="${ACR_BUILD_MODE:-auto}"

if [[ "$ACR_BUILD_MODE" != "auto" && "$ACR_BUILD_MODE" != "remote" && "$ACR_BUILD_MODE" != "local" ]]; then
  echo "ACR_BUILD_MODE must be auto, remote, or local." >&2
  exit 1
fi

ACR_LOGIN_SERVER="$(az acr show -n "$ACR_NAME" -g "$RESOURCE_GROUP" --query loginServer -o tsv)"
ACR_USERNAME="$(az acr credential show -n "$ACR_NAME" --query username -o tsv)"
ACR_PASSWORD="$(az acr credential show -n "$ACR_NAME" --query passwords[0].value -o tsv)"
API_IMAGE="${ACR_LOGIN_SERVER}/${PREFIX}-api:latest"
MIGRATE_IMAGE="${ACR_LOGIN_SERVER}/${PREFIX}-migrate:latest"
FRONTEND_IMAGE="${ACR_LOGIN_SERVER}/${PREFIX}-frontend:latest"

resolved_acr_build_mode="$ACR_BUILD_MODE"
local_build_ready="false"

ensure_local_build_ready() {
  if [[ "$local_build_ready" == "true" ]]; then
    return 0
  fi

  if ! command -v docker >/dev/null 2>&1; then
    echo "Docker CLI is required for local image builds. Install Docker or set ACR_BUILD_MODE=remote." >&2
    exit 1
  fi

  if ! docker info >/dev/null 2>&1; then
    echo "Docker daemon is not running. Start Docker or set ACR_BUILD_MODE=remote." >&2
    exit 1
  fi

  printf '%s' "$ACR_PASSWORD" | docker login "$ACR_LOGIN_SERVER" --username "$ACR_USERNAME" --password-stdin >/dev/null
  local_build_ready="true"
}

build_image_local() {
  local full_image="$1"
  local dockerfile="$2"
  local context="$3"
  ensure_local_build_ready
  docker build -t "$full_image" -f "$dockerfile" "$context"
  docker push "$full_image"
}

build_image() {
  local short_tag="$1"
  local full_image="$2"
  local dockerfile="$3"
  local context="$4"

  if [[ "$resolved_acr_build_mode" == "local" ]]; then
    build_image_local "$full_image" "$dockerfile" "$context"
    return 0
  fi

  if [[ "$resolved_acr_build_mode" == "remote" ]]; then
    az acr build -r "$ACR_NAME" -t "$short_tag" -f "$dockerfile" "$context"
    return 0
  fi

  local build_output
  if build_output="$(az acr build -r "$ACR_NAME" -t "$short_tag" -f "$dockerfile" "$context" 2>&1)"; then
    printf '%s\n' "$build_output"
    return 0
  fi

  printf '%s\n' "$build_output" >&2
  if grep -q "TasksOperationsNotAllowed" <<<"$build_output"; then
    echo "ACR Tasks are not allowed in this subscription. Falling back to local Docker build/push." >&2
    resolved_acr_build_mode="local"
    build_image_local "$full_image" "$dockerfile" "$context"
    return 0
  fi

  return 1
}

build_image "${PREFIX}-api:latest" "$API_IMAGE" "Dockerfile" "."
build_image "${PREFIX}-migrate:latest" "$MIGRATE_IMAGE" "Dockerfile.migrate" "."
build_image "${PREFIX}-frontend:latest" "$FRONTEND_IMAGE" "frontend/Dockerfile" "./frontend"

az containerapp update -g "$RESOURCE_GROUP" -n "${PREFIX}-api" --image "$API_IMAGE" >/dev/null
az containerapp update -g "$RESOURCE_GROUP" -n "${PREFIX}-frontend" --image "$FRONTEND_IMAGE" >/dev/null
az containerapp job update -g "$RESOURCE_GROUP" -n "${PREFIX}-migrate" --image "$MIGRATE_IMAGE" >/dev/null

echo "Images rebuilt and Container Apps updated."
