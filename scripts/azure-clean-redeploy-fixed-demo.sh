#!/usr/bin/env bash
set -euo pipefail

# azure-clean-redeploy-fixed-demo.sh
#
# Clean Azure redeploy with known demo passwords.
# It deletes the whole resource group, removes stale .azure-deploy.env,
# forces local Docker build/push, then runs scripts/azure-deploy.sh.
#
# Default target:
#   RESOURCE_GROUP=rg-mojeapp
#   PREFIX=mojeapp
#   LOCATION=westus2
#
# Required destructive confirmation:
#   CONFIRM_DELETE=rg-mojeapp ./azure-clean-redeploy-fixed-demo.sh
#
# After success, demo credentials:
#   admin   / admin123
#   curator / curator123
#   analyst / analyst123
#   user    / user123

find_repo_root() {
  local d
  d="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

  if [[ -f "$d/scripts/azure-deploy.sh" || -f "$d/azure-deploy.sh" || -d "$d/infra" ]]; then
    printf '%s\n' "$d"
    return
  fi

  if [[ -f "$d/../scripts/azure-deploy.sh" || -f "$d/../azure-deploy.sh" || -d "$d/../infra" ]]; then
    cd "$d/.." && pwd
    return
  fi

  echo "Cannot find repo root. Put this file in repo root or scripts/." >&2
  exit 1
}

ROOT_DIR="$(find_repo_root)"
cd "$ROOT_DIR"

ENV_FILE="$ROOT_DIR/.azure-deploy.env"

# Load old env only to reuse RESOURCE_GROUP / PREFIX / LOCATION if the caller did not set them.
# Demo passwords are overwritten below unconditionally.
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

RESOURCE_GROUP="${RESOURCE_GROUP:-rg-mojeapp}"
PREFIX="${PREFIX:-mojeapp}"
LOCATION="${LOCATION:-westus2}"

if [[ "${CONFIRM_DELETE:-}" != "$RESOURCE_GROUP" ]]; then
  cat >&2 <<EOF
Refusing to delete Azure resources without explicit confirmation.

This will delete the whole resource group:
  $RESOURCE_GROUP

Run exactly:
  CONFIRM_DELETE=$RESOURCE_GROUP $0

Optional overrides:
  RESOURCE_GROUP=rg-mojeapp PREFIX=mojeapp LOCATION=westus2 CONFIRM_DELETE=rg-mojeapp $0
EOF
  exit 2
fi

echo "Azure account:"
az account show --query "{subscription:name, id:id, tenant:tenantDisplayName}" -o table
echo

echo "Deleting resource group: $RESOURCE_GROUP"
az group delete --name "$RESOURCE_GROUP" --yes --no-wait 2>/dev/null || true

echo "Waiting for resource group deletion..."
az group wait --name "$RESOURCE_GROUP" --deleted 2>/dev/null || true

echo "Removing stale local deployment env: $ENV_FILE"
rm -f "$ENV_FILE"

# Avoid Docker credential helper/pass issue by forcing a clean Docker config.
export DOCKER_CONFIG="$ROOT_DIR/.docker-acr-temp"
rm -rf "$DOCKER_CONFIG"
mkdir -p "$DOCKER_CONFIG"

# Force known clean deployment settings.
export RESOURCE_GROUP="$RESOURCE_GROUP"
export PREFIX="$PREFIX"
export LOCATION="$LOCATION"
export START_ENABLED="${START_ENABLED_OVERRIDE:-true}"
export ACR_BUILD_MODE="${ACR_BUILD_MODE_OVERRIDE:-local}"
export SEED_DEMO_USERS=true

# Force known demo passwords. Do NOT preserve values from old .azure-deploy.env.
export DEMO_ADMIN_PASSWORD="${DEMO_ADMIN_PASSWORD_OVERRIDE:-admin123}"
export DEMO_CURATOR_PASSWORD="${DEMO_CURATOR_PASSWORD_OVERRIDE:-curator123}"
export DEMO_ANALYST_PASSWORD="${DEMO_ANALYST_PASSWORD_OVERRIDE:-analyst123}"
export DEMO_USER_PASSWORD="${DEMO_USER_PASSWORD_OVERRIDE:-user123}"

# Do not preserve old ACR_NAME from .azure-deploy.env unless explicitly requested.
unset ACR_NAME
if [[ -n "${ACR_NAME_OVERRIDE:-}" ]]; then
  export ACR_NAME="$ACR_NAME_OVERRIDE"
fi

echo
echo "Redeploy settings:"
echo "  RESOURCE_GROUP=$RESOURCE_GROUP"
echo "  PREFIX=$PREFIX"
echo "  LOCATION=$LOCATION"
echo "  START_ENABLED=$START_ENABLED"
echo "  ACR_BUILD_MODE=$ACR_BUILD_MODE"
echo "  DOCKER_CONFIG=$DOCKER_CONFIG"
echo
echo "Forced demo credentials:"
echo "  admin   / $DEMO_ADMIN_PASSWORD"
echo "  curator / $DEMO_CURATOR_PASSWORD"
echo "  analyst / $DEMO_ANALYST_PASSWORD"
echo "  user    / $DEMO_USER_PASSWORD"
echo

if [[ -x "$ROOT_DIR/scripts/azure-deploy.sh" ]]; then
  DEPLOY_SCRIPT="$ROOT_DIR/scripts/azure-deploy.sh"
elif [[ -x "$ROOT_DIR/azure-deploy.sh" ]]; then
  DEPLOY_SCRIPT="$ROOT_DIR/azure-deploy.sh"
else
  echo "Cannot find executable azure-deploy.sh. Expected scripts/azure-deploy.sh or azure-deploy.sh." >&2
  exit 1
fi

echo "Running deploy script: $DEPLOY_SCRIPT"
"$DEPLOY_SCRIPT"

echo
echo "Deployment script finished."

if az containerapp job show -g "$RESOURCE_GROUP" -n "${PREFIX}-migrate" >/dev/null 2>&1; then
  echo
  echo "Starting migration/seed job: ${PREFIX}-migrate"
  az containerapp job start -g "$RESOURCE_GROUP" -n "${PREFIX}-migrate" >/dev/null

  sleep 8
  EXECUTION_NAME="$(az containerapp job execution list \
    -g "$RESOURCE_GROUP" \
    -n "${PREFIX}-migrate" \
    --query "sort_by(@,&properties.startTime)[-1].name" \
    -o tsv)"

  if [[ -n "$EXECUTION_NAME" ]]; then
    echo "Migration execution: $EXECUTION_NAME"
    elapsed=0
    timeout=900

    while true; do
      status="$(az containerapp job execution show \
        -g "$RESOURCE_GROUP" \
        -n "${PREFIX}-migrate" \
        --job-execution-name "$EXECUTION_NAME" \
        --query "properties.status" \
        -o tsv 2>/dev/null || echo Unknown)"

      echo "  migration status=$status elapsed=${elapsed}s"

      case "$status" in
        Succeeded)
          echo "Migration/seed job succeeded."
          break
          ;;
        Failed|Error)
          echo "Migration/seed job failed. Logs:" >&2
          az containerapp job logs show \
            -g "$RESOURCE_GROUP" \
            -n "${PREFIX}-migrate" \
            --job-execution-name "$EXECUTION_NAME" \
            --tail 300 2>/dev/null || true
          exit 1
          ;;
      esac

      if [[ "$elapsed" -ge "$timeout" ]]; then
        echo "Timeout waiting for migration/seed job." >&2
        echo "Check:"
        echo "  az containerapp job logs show -g \"$RESOURCE_GROUP\" -n \"${PREFIX}-migrate\" --job-execution-name \"$EXECUTION_NAME\" --tail 300"
        exit 1
      fi

      sleep 10
      elapsed=$((elapsed + 10))
    done
  fi
else
  echo "No migration job found at ${PREFIX}-migrate. Skipping explicit seed run."
fi

echo
echo "Container Apps:"
az containerapp list -g "$RESOURCE_GROUP" --query "[].{name:name,fqdn:properties.configuration.ingress.fqdn,provisioning:properties.provisioningState}" -o table || true

echo
echo "Done."
echo "Try login:"
echo "  admin   / $DEMO_ADMIN_PASSWORD"
echo "  curator / $DEMO_CURATOR_PASSWORD"
echo "  analyst / $DEMO_ANALYST_PASSWORD"
echo "  user    / $DEMO_USER_PASSWORD"
