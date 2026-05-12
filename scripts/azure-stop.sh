#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.azure-deploy.env"

_EXTERNAL_RESOURCE_GROUP="${RESOURCE_GROUP-}"
_EXTERNAL_PREFIX="${PREFIX-}"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

[[ -n "$_EXTERNAL_RESOURCE_GROUP" ]] && RESOURCE_GROUP="$_EXTERNAL_RESOURCE_GROUP"
[[ -n "$_EXTERNAL_PREFIX" ]] && PREFIX="$_EXTERNAL_PREFIX"

RESOURCE_GROUP="${RESOURCE_GROUP:-rg-xdub-2220}"
PREFIX="${PREFIX:-xdubrag}"

for app in "${PREFIX}-frontend" "${PREFIX}-api" "${PREFIX}-qdrant" "${PREFIX}-postgres"; do
  az containerapp update -g "$RESOURCE_GROUP" -n "$app" --min-replicas 0 --max-replicas 1 >/dev/null
  echo "Scaled to zero: $app"
done

echo "Stopped compute. Azure Files, ACR, Log Analytics, and the Container Apps environment remain provisioned."
