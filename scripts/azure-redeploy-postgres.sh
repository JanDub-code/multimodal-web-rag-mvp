#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
ENV_FILE="$ROOT_DIR/.azure-deploy.env"

_EXTERNAL_RESOURCE_GROUP="${RESOURCE_GROUP-}"
_EXTERNAL_LOCATION="${LOCATION-}"
_EXTERNAL_PREFIX="${PREFIX-}"
_EXTERNAL_POSTGRES_PASSWORD="${POSTGRES_PASSWORD-}"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

[[ -n "$_EXTERNAL_RESOURCE_GROUP" ]] && RESOURCE_GROUP="$_EXTERNAL_RESOURCE_GROUP"
[[ -n "$_EXTERNAL_LOCATION" ]] && LOCATION="$_EXTERNAL_LOCATION"
[[ -n "$_EXTERNAL_PREFIX" ]] && PREFIX="$_EXTERNAL_PREFIX"
[[ -n "$_EXTERNAL_POSTGRES_PASSWORD" ]] && POSTGRES_PASSWORD="$_EXTERNAL_POSTGRES_PASSWORD"

RESOURCE_GROUP="${RESOURCE_GROUP:-rg-xdub-2220}"
LOCATION="${LOCATION:-westus2}"
PREFIX="${PREFIX:-xdubrag}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD or source .azure-deploy.env first.}"

if [[ ! "$PREFIX" =~ ^[a-z0-9][a-z0-9-]{1,18}[a-z0-9]$ ]]; then
  echo "PREFIX must be lowercase letters/numbers/hyphen, 3-20 chars, no leading/trailing hyphen." >&2
  exit 1
fi

az account show >/dev/null
az extension add -n containerapp --upgrade >/dev/null
az provider register --namespace Microsoft.App --wait >/dev/null

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

wait_job_execution() {
  local job_name="$1"
  local execution_name="$2"
  local timeout="${3:-600}"
  local elapsed=0

  while true; do
    local status
    status="$(az containerapp job execution show -g "$RESOURCE_GROUP" -n "$job_name" --job-execution-name "$execution_name" --query properties.status -o tsv 2>/dev/null || echo Unknown)"
    case "$status" in
      Succeeded) return 0 ;;
      Failed|Error)
        echo "Migration job failed. Check Container Apps Job execution logs: $execution_name" >&2
        return 1
        ;;
    esac

    if [[ "$elapsed" -ge "$timeout" ]]; then
      echo "Timeout waiting for migration job: $execution_name" >&2
      return 1
    fi

    sleep 10
    elapsed=$((elapsed + 10))
  done
}

echo "Redeploying only Postgres for prefix '$PREFIX' in resource group '$RESOURCE_GROUP'..."

az deployment group create \
  --resource-group "$RESOURCE_GROUP" \
  --template-file infra/postgres-only.bicep \
  --parameters \
    location="$LOCATION" \
    prefix="$PREFIX" \
    postgresPassword="$POSTGRES_PASSWORD" >/dev/null

wait_replicas "${PREFIX}-postgres" 1 420

JOB_NAME="${PREFIX}-migrate"
echo "Starting migration and seed job: $JOB_NAME"
az containerapp job start -g "$RESOURCE_GROUP" -n "$JOB_NAME" >/dev/null
sleep 5
EXECUTION_NAME="$(az containerapp job execution list -g "$RESOURCE_GROUP" -n "$JOB_NAME" --query "sort_by(@,&properties.startTime)[-1].name" -o tsv)"
wait_job_execution "$JOB_NAME" "$EXECUTION_NAME" 600

echo "Postgres redeploy finished."
echo "Check logs with: az containerapp logs show -g \"$RESOURCE_GROUP\" -n \"${PREFIX}-postgres\" --tail 100"
echo "Default accounts were re-seeded by job: $JOB_NAME"