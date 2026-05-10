#!/usr/bin/env bash
# dev-up.sh — robustní startovací skript pro lokální vývoj
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# ── pomocné funkce ──────────────────────────────────────────────────────────

log()  { echo "[dev-up] $*"; }
die()  { echo "[dev-up] ERROR: $*" >&2; exit 1; }

# Vymaže všechny project-kontejnery (i zaseknuts stopped), ignoruje chyby
cleanup_containers() {
  local containers=(local-mvp-postgres local-mvp-qdrant local-mvp-api local-mvp-frontend local-mvp-migrate)
  log "Odstraňuji staré kontejnery..."
  docker rm -f "${containers[@]}" 2>/dev/null || true
}

wait_healthy() {
  local container="$1"
  local max_secs="${2:-60}"
  local elapsed=0
  log "Čekám na zdraví kontejneru '$container' (max ${max_secs}s)..."
  until [[ "$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null)" == "healthy" ]]; do
    sleep 2; elapsed=$((elapsed + 2))
    [[ $elapsed -ge $max_secs ]] && die "Kontejner '$container' není healthy po ${max_secs}s. Zkontroluj: docker logs $container"
  done
  log "$container ✔ healthy"
}

verify_users() {
  local count
  count="$(docker compose exec -T postgres psql -U app -d multimodal_mvp -tAc \
    "SELECT count(*) FROM users WHERE username IN ('admin','curator','analyst','user');" | tr -d '[:space:]')"
  [[ "$count" == "4" ]] || die "Uživatelé se nevy tvořili správně (${count:-0}/4). Zkus: make seed"
}

# ── hlavní logika ────────────────────────────────────────────────────────────

BUILD_FLAG=""
FORCE_FLAG=""

# Volitelné argumenty
for arg in "$@"; do
  case "$arg" in
    --build)  BUILD_FLAG="--build" ;;
    --force)  FORCE_FLAG="--force-recreate" ;;
    --clean)  cleanup_containers ;;
    *)        die "Neznámý argument: $arg. Podporované: --build, --force, --clean" ;;
  esac
done

log "=== START ==="

# 1. Odstraň konflikty (stopped kontejnery se stejným jménem)
cleanup_containers

# 2. Spusť infra services
log "Spouštím postgres a qdrant..."
docker compose up -d postgres qdrant

# 3. Počkej na postgres
wait_healthy local-mvp-postgres 90

# 4. Migrace
log "Spouštím databázové migrace..."
docker compose --profile tools run --rm migrate

# 5. Seed uživatelů
log "Seeduji výchozí uživatele..."
docker compose --profile tools run --rm migrate python -m scripts.init_db

# 6. Ověř uživatele
verify_users

# 7. Spusť api + frontend
log "Spouštím api a frontend..."
docker compose up -d $BUILD_FLAG $FORCE_FLAG api frontend

echo ""
echo "══════════════════════════════════════════"
echo "  ✔  Stack běží!"
echo "  Frontend : http://127.0.0.1:8080"
echo "  API      : http://127.0.0.1:8000"
echo "  Health   : http://127.0.0.1:8000/health"
echo "══════════════════════════════════════════"
echo ""
echo "  Přihlášení:"
echo "    admin    / admin123"
echo "    curator  / curator123"
echo "    analyst  / analyst123"
echo "    user     / user123"
echo ""
echo "  OpenCode API klíč (volitelný):"
echo "    OPENCODE_API_KEY='sk-...' ./scripts/dev-up.sh"
echo "══════════════════════════════════════════"
