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

wait_replicas() {
  local app="$1"
  local wanted="${2:-1}"
  local timeout="${3:-420}"
  local elapsed=0
  while true; do
    local count
    count="$(az containerapp replica list -g "$RESOURCE_GROUP" -n "$app" --query "length([?properties.runningState=='Running'])" -o tsv 2>/dev/null || echo 0)"
    if [[ "${count:-0}" -ge "$wanted" ]]; then
      return 0
    fi
    if [[ "$elapsed" -ge "$timeout" ]]; then
      echo "Timeout waiting for $app replicas. Check logs in Azure Portal." >&2
      return 1
    fi
    sleep 10
    elapsed=$((elapsed + 10))
  done
}

az containerapp update -g "$RESOURCE_GROUP" -n "${PREFIX}-postgres" --min-replicas 1 --max-replicas 1 >/dev/null
wait_replicas "${PREFIX}-postgres" 1 420

az containerapp update -g "$RESOURCE_GROUP" -n "${PREFIX}-qdrant" --min-replicas 1 --max-replicas 1 >/dev/null
wait_replicas "${PREFIX}-qdrant" 1 420

JOB_NAME="${PREFIX}-migrate"
az containerapp job start -g "$RESOURCE_GROUP" -n "$JOB_NAME" >/dev/null
sleep 5
EXECUTION_NAME="$(az containerapp job execution list -g "$RESOURCE_GROUP" -n "$JOB_NAME" --query "sort_by(@,&properties.startTime)[-1].name" -o tsv)"
elapsed=0
while true; do
  STATUS="$(az containerapp job execution show -g "$RESOURCE_GROUP" -n "$JOB_NAME" --job-execution-name "$EXECUTION_NAME" --query properties.status -o tsv 2>/dev/null || echo Unknown)"
  case "$STATUS" in
    Succeeded) break ;;
    Failed|Error) echo "Migration job failed. Check Container Apps Job execution logs: $EXECUTION_NAME" >&2; exit 1 ;;
  esac
  if [[ "$elapsed" -ge 600 ]]; then
    echo "Timeout waiting for migration job: $EXECUTION_NAME" >&2
    exit 1
  fi
  sleep 10
  elapsed=$((elapsed + 10))
done

az containerapp update -g "$RESOURCE_GROUP" -n "${PREFIX}-api" --min-replicas 1 --max-replicas 1 >/dev/null
wait_replicas "${PREFIX}-api" 1 600

az containerapp update -g "$RESOURCE_GROUP" -n "${PREFIX}-frontend" --min-replicas 1 --max-replicas 1 >/dev/null
wait_replicas "${PREFIX}-frontend" 1 420

FQDN="$(az containerapp show -g "$RESOURCE_GROUP" -n "${PREFIX}-frontend" --query properties.configuration.ingress.fqdn -o tsv)"
echo "Running: https://$FQDN"

if [[ "${SEED_DEMO_USERS:-true}" == "true" ]]; then
  echo ""
  echo "Demo users:"
  echo "  admin   / ${DEMO_ADMIN_PASSWORD:-admin123}"
  echo "  curator / ${DEMO_CURATOR_PASSWORD:-curator123}"
  echo "  analyst / ${DEMO_ANALYST_PASSWORD:-analyst123}"
  echo "  user    / ${DEMO_USER_PASSWORD:-user123}"
fi
