#!/usr/bin/env bash
set -euo pipefail

# Backward-compatible entrypoint.
# Keep older docs/scripts working while using the improved deploy flow.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "$ROOT_DIR/scripts/azure-deploy.fixed.sh" "$@"
