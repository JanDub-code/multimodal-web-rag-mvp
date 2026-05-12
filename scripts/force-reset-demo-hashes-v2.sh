#!/usr/bin/env bash
set -euo pipefail

# force-reset-demo-hashes-v2.sh
#
# Direct DB password-hash overwrite for deployed demo users.
# This version avoids Azure CLI multiline --args parsing by starting the existing
# migrate job with a one-shot YAML/JSON template override.
#
# Default credentials after success:
#   admin   / admin123
#   curator / curator123
#   analyst / analyst123
#   user    / user123
#
# Run from repo root or scripts/:
#   chmod +x force-reset-demo-hashes-v2.sh
#   ./force-reset-demo-hashes-v2.sh
#
# Optional:
#   RESOURCE_GROUP=rg-xdub-2220 PREFIX=xdubrag ./force-reset-demo-hashes-v2.sh
#   DATABASE_URL='postgresql://postgres:<password>@xdubrag-postgres:5432/postgres' ./force-reset-demo-hashes-v2.sh
#   DEMO_ADMIN_PASSWORD='newpass' ./force-reset-demo-hashes-v2.sh

find_repo_root() {
  local d
  d="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

  if [[ -f "$d/.azure-deploy.env" || -d "$d/infra" ]]; then
    printf '%s\n' "$d"
    return
  fi

  if [[ -f "$d/../.azure-deploy.env" || -d "$d/../infra" ]]; then
    cd "$d/.." && pwd
    return
  fi

  pwd
}

ROOT_DIR="$(find_repo_root)"
cd "$ROOT_DIR"

ENV_FILE="$ROOT_DIR/.azure-deploy.env"

_EXTERNAL_RESOURCE_GROUP="${RESOURCE_GROUP-}"
_EXTERNAL_PREFIX="${PREFIX-}"
_EXTERNAL_POSTGRES_PASSWORD="${POSTGRES_PASSWORD-}"
_EXTERNAL_DATABASE_URL="${DATABASE_URL-}"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

[[ -n "$_EXTERNAL_RESOURCE_GROUP" ]] && RESOURCE_GROUP="$_EXTERNAL_RESOURCE_GROUP"
[[ -n "$_EXTERNAL_PREFIX" ]] && PREFIX="$_EXTERNAL_PREFIX"
[[ -n "$_EXTERNAL_POSTGRES_PASSWORD" ]] && POSTGRES_PASSWORD="$_EXTERNAL_POSTGRES_PASSWORD"
[[ -n "$_EXTERNAL_DATABASE_URL" ]] && DATABASE_URL="$_EXTERNAL_DATABASE_URL"

RESOURCE_GROUP="${RESOURCE_GROUP:-rg-xdub-2220}"
PREFIX="${PREFIX:-xdubrag}"
MIGRATE_JOB="${JOB_NAME:-${PREFIX}-migrate}"

DEMO_ADMIN_PASSWORD="${DEMO_ADMIN_PASSWORD:-admin123}"
DEMO_CURATOR_PASSWORD="${DEMO_CURATOR_PASSWORD:-curator123}"
DEMO_ANALYST_PASSWORD="${DEMO_ANALYST_PASSWORD:-analyst123}"
DEMO_USER_PASSWORD="${DEMO_USER_PASSWORD:-user123}"

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing command: $1" >&2
    exit 1
  fi
}

need_cmd az
need_cmd python3
need_cmd base64

base64_one_line() {
  if base64 --help 2>&1 | grep -q -- '-w'; then
    base64 -w0
  else
    base64 | tr -d '\n'
  fi
}

url_encode() {
  python3 - "$1" <<'PY'
import sys, urllib.parse
print(urllib.parse.quote(sys.argv[1], safe=""))
PY
}

echo "Using:"
echo "  ROOT_DIR=$ROOT_DIR"
echo "  RESOURCE_GROUP=$RESOURCE_GROUP"
echo "  PREFIX=$PREFIX"
echo "  MIGRATE_JOB=$MIGRATE_JOB"
echo

az account show >/dev/null

TMP_DIR="$(mktemp -d)"
JOB_JSON="$TMP_DIR/job.json"
SECRETS_JSON="$TMP_DIR/secrets.json"
SQL_FILE="$TMP_DIR/reset-demo-passwords.sql"
TEMPLATE_FILE="$TMP_DIR/reset-template.yaml"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

echo "Reading migrate job config..."
az containerapp job show \
  --resource-group "$RESOURCE_GROUP" \
  --name "$MIGRATE_JOB" \
  -o json > "$JOB_JSON"

az containerapp job secret list \
  --resource-group "$RESOURCE_GROUP" \
  --name "$MIGRATE_JOB" \
  -o json > "$SECRETS_JSON" 2>/dev/null || echo '[]' > "$SECRETS_JSON"

get_job_env() {
  local env_name="$1"
  python3 - "$env_name" "$JOB_JSON" "$SECRETS_JSON" <<'PY'
import json, sys

name = sys.argv[1]
job_path = sys.argv[2]
secrets_path = sys.argv[3]

with open(job_path, "r", encoding="utf-8") as f:
    job = json.load(f)

try:
    with open(secrets_path, "r", encoding="utf-8") as f:
        secrets = json.load(f)
except Exception:
    secrets = []

envs = (
    job.get("properties", {})
       .get("template", {})
       .get("containers", [{}])[0]
       .get("env", [])
)

secret_by_name = {
    s.get("name"): s.get("value")
    for s in secrets
    if isinstance(s, dict)
}

for e in envs:
    if e.get("name") != name:
        continue

    value = e.get("value")
    if value not in (None, "", "null"):
        print(value)
        sys.exit(0)

    ref = e.get("secretRef")
    if ref and secret_by_name.get(ref):
        print(secret_by_name[ref])
        sys.exit(0)

sys.exit(0)
PY
}

DB_URL="${DATABASE_URL:-}"

if [[ -z "$DB_URL" ]]; then
  for candidate in DATABASE_URL SQLALCHEMY_DATABASE_URI POSTGRES_URL POSTGRES_URI POSTGRES_DSN DB_URL; do
    value="$(get_job_env "$candidate" || true)"
    if [[ -n "$value" ]]; then
      DB_URL="$value"
      break
    fi
  done
fi

if [[ -z "$DB_URL" ]]; then
  PGHOST="$(get_job_env POSTGRES_HOST || true)"
  [[ -z "$PGHOST" ]] && PGHOST="$(get_job_env PGHOST || true)"
  [[ -z "$PGHOST" ]] && PGHOST="$(get_job_env DATABASE_HOST || true)"
  [[ -z "$PGHOST" ]] && PGHOST="${PREFIX}-postgres"

  PGPORT="$(get_job_env POSTGRES_PORT || true)"
  [[ -z "$PGPORT" ]] && PGPORT="$(get_job_env PGPORT || true)"
  [[ -z "$PGPORT" ]] && PGPORT="5432"

  PGUSER="$(get_job_env POSTGRES_USER || true)"
  [[ -z "$PGUSER" ]] && PGUSER="$(get_job_env PGUSER || true)"
  [[ -z "$PGUSER" ]] && PGUSER="postgres"

  PGPASSWORD_VALUE="${POSTGRES_PASSWORD:-}"
  [[ -z "$PGPASSWORD_VALUE" ]] && PGPASSWORD_VALUE="$(get_job_env POSTGRES_PASSWORD || true)"
  [[ -z "$PGPASSWORD_VALUE" ]] && PGPASSWORD_VALUE="$(get_job_env PGPASSWORD || true)"

  PGDATABASE="$(get_job_env POSTGRES_DB || true)"
  [[ -z "$PGDATABASE" ]] && PGDATABASE="$(get_job_env PGDATABASE || true)"
  [[ -z "$PGDATABASE" ]] && PGDATABASE="$(get_job_env DATABASE_NAME || true)"
  [[ -z "$PGDATABASE" ]] && PGDATABASE="postgres"

  if [[ -n "$PGHOST" && -n "$PGPASSWORD_VALUE" ]]; then
    PGUSER_ENC="$(url_encode "$PGUSER")"
    PGPASSWORD_ENC="$(url_encode "$PGPASSWORD_VALUE")"
    DB_URL="postgresql://${PGUSER_ENC}:${PGPASSWORD_ENC}@${PGHOST}:${PGPORT}/${PGDATABASE}"
  fi
fi

if [[ -z "$DB_URL" ]]; then
  cat >&2 <<EOF
Could not infer DATABASE_URL.

Run with explicit DATABASE_URL, for example:
  DATABASE_URL='postgresql://postgres:<password>@${PREFIX}-postgres:5432/postgres' ./force-reset-demo-hashes-v2.sh

Or inspect migrate job env:
  az containerapp job show -g "$RESOURCE_GROUP" -n "$MIGRATE_JOB" --query "properties.template.containers[0].env" -o table
EOF
  exit 1
fi

echo "Database URL inferred. Password will not be printed."

cat > "$SQL_FILE" <<'SQL'
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TEMP TABLE _reset_demo_passwords (
  login text PRIMARY KEY,
  plaintext text NOT NULL
) ON COMMIT DROP;

INSERT INTO _reset_demo_passwords(login, plaintext) VALUES
  ('admin',   :'admin_password'),
  ('curator', :'curator_password'),
  ('analyst', :'analyst_password'),
  ('user',    :'user_password');

DO $$
DECLARE
  tbl record;
  acct record;
  where_sql text;
  sep text;
  n integer;
  total integer := 0;
BEGIN
  FOR tbl IN
    WITH base_tables AS (
      SELECT table_schema, table_name
      FROM information_schema.tables
      WHERE table_type = 'BASE TABLE'
        AND table_schema NOT IN ('pg_catalog', 'information_schema')
    )
    SELECT
      bt.table_schema,
      bt.table_name,
      (
        SELECT c.column_name
        FROM information_schema.columns c
        WHERE c.table_schema = bt.table_schema
          AND c.table_name = bt.table_name
          AND c.column_name IN ('password_hash', 'hashed_password', 'password_digest', 'password')
        ORDER BY CASE c.column_name
          WHEN 'password_hash' THEN 1
          WHEN 'hashed_password' THEN 2
          WHEN 'password_digest' THEN 3
          WHEN 'password' THEN 4
          ELSE 99
        END
        LIMIT 1
      ) AS pass_col,
      (
        SELECT c.column_name
        FROM information_schema.columns c
        WHERE c.table_schema = bt.table_schema
          AND c.table_name = bt.table_name
          AND c.column_name IN ('username', 'user_name', 'login', 'name', 'handle')
        ORDER BY CASE c.column_name
          WHEN 'username' THEN 1
          WHEN 'user_name' THEN 2
          WHEN 'login' THEN 3
          WHEN 'name' THEN 4
          WHEN 'handle' THEN 5
          ELSE 99
        END
        LIMIT 1
      ) AS login_col,
      (
        SELECT c.column_name
        FROM information_schema.columns c
        WHERE c.table_schema = bt.table_schema
          AND c.table_name = bt.table_name
          AND c.column_name IN ('email', 'email_address')
        ORDER BY CASE c.column_name
          WHEN 'email' THEN 1
          WHEN 'email_address' THEN 2
          ELSE 99
        END
        LIMIT 1
      ) AS email_col,
      (
        SELECT c.column_name
        FROM information_schema.columns c
        WHERE c.table_schema = bt.table_schema
          AND c.table_name = bt.table_name
          AND c.column_name IN ('role', 'role_name')
        ORDER BY CASE c.column_name
          WHEN 'role' THEN 1
          WHEN 'role_name' THEN 2
          ELSE 99
        END
        LIMIT 1
      ) AS role_col
    FROM base_tables bt
  LOOP
    IF tbl.pass_col IS NULL THEN
      CONTINUE;
    END IF;

    IF tbl.login_col IS NULL AND tbl.email_col IS NULL AND tbl.role_col IS NULL THEN
      CONTINUE;
    END IF;

    FOR acct IN SELECT login, plaintext FROM _reset_demo_passwords LOOP
      where_sql := '';
      sep := '';

      IF tbl.login_col IS NOT NULL THEN
        where_sql := where_sql || sep || format(
          '(lower(%1$I::text) = %2$L OR lower(%1$I::text) LIKE %3$L)',
          tbl.login_col,
          acct.login,
          acct.login || '@%'
        );
        sep := ' OR ';
      END IF;

      IF tbl.email_col IS NOT NULL THEN
        where_sql := where_sql || sep || format(
          '(lower(%1$I::text) = %2$L OR lower(%1$I::text) LIKE %3$L)',
          tbl.email_col,
          acct.login,
          acct.login || '@%'
        );
        sep := ' OR ';
      END IF;

      IF tbl.login_col IS NULL AND tbl.email_col IS NULL AND tbl.role_col IS NOT NULL THEN
        where_sql := where_sql || sep || format('lower(%I::text) = %L', tbl.role_col, acct.login);
      END IF;

      IF where_sql = '' THEN
        CONTINUE;
      END IF;

      EXECUTE format(
        'UPDATE %I.%I SET %I = crypt(%L, gen_salt(''bf'', 12)) WHERE %s',
        tbl.table_schema,
        tbl.table_name,
        tbl.pass_col,
        acct.plaintext,
        where_sql
      );

      GET DIAGNOSTICS n = ROW_COUNT;

      IF n > 0 THEN
        total := total + n;
        RAISE NOTICE 'updated table=%.% account=% rows=% password_column=%',
          tbl.table_schema,
          tbl.table_name,
          acct.login,
          n,
          tbl.pass_col;
      END IF;
    END LOOP;
  END LOOP;

  IF total = 0 THEN
    RAISE EXCEPTION 'No demo user rows were updated. Could not match users by username/email/role columns.';
  END IF;

  RAISE NOTICE 'total updated rows=%', total;
END $$;
SQL

SQL_B64="$(base64_one_line < "$SQL_FILE")"

RUNNER='set -eu
printf "%s" "$RESET_SQL_B64" | base64 -d > /tmp/reset-demo-passwords.sql
DBURL="${RESET_DATABASE_URL:-}"
if [ -z "$DBURL" ]; then
  echo "RESET_DATABASE_URL is empty" >&2
  exit 2
fi
DBURL="$(printf "%s" "$DBURL" | sed "s#^postgresql+asyncpg://#postgresql://#; s#^postgresql+psycopg://#postgresql://#; s#^postgresql+psycopg2://#postgresql://#; s#^postgres://#postgresql://#")"
echo "Running password hash reset SQL..."
psql "$DBURL" \
  -v ON_ERROR_STOP=1 \
  -v admin_password="$DEMO_ADMIN_PASSWORD" \
  -v curator_password="$DEMO_CURATOR_PASSWORD" \
  -v analyst_password="$DEMO_ANALYST_PASSWORD" \
  -v user_password="$DEMO_USER_PASSWORD" \
  -f /tmp/reset-demo-passwords.sql
echo "Password hash reset finished."
'

python3 - "$TEMPLATE_FILE" "$RUNNER" "$SQL_B64" "$DB_URL" "$DEMO_ADMIN_PASSWORD" "$DEMO_CURATOR_PASSWORD" "$DEMO_ANALYST_PASSWORD" "$DEMO_USER_PASSWORD" <<'PY'
import json, sys

template_file, runner, sql_b64, db_url, admin_pw, curator_pw, analyst_pw, user_pw = sys.argv[1:]

template = {
    "containers": [
        {
            "name": "reset-hashes",
            "image": "postgres:16-alpine",
            "command": ["/bin/sh"],
            "args": ["-lc", runner],
            "resources": {
                "cpu": 0.25,
                "memory": "0.5Gi"
            },
            "env": [
                {"name": "RESET_SQL_B64", "value": sql_b64},
                {"name": "RESET_DATABASE_URL", "value": db_url},
                {"name": "DEMO_ADMIN_PASSWORD", "value": admin_pw},
                {"name": "DEMO_CURATOR_PASSWORD", "value": curator_pw},
                {"name": "DEMO_ANALYST_PASSWORD", "value": analyst_pw},
                {"name": "DEMO_USER_PASSWORD", "value": user_pw},
            ],
        }
    ]
}

with open(template_file, "w", encoding="utf-8") as f:
    json.dump(template, f, indent=2)
PY

echo "Starting existing job with one-shot postgres reset template override..."
az containerapp job start \
  --resource-group "$RESOURCE_GROUP" \
  --name "$MIGRATE_JOB" \
  --yaml "$TEMPLATE_FILE" \
  --only-show-errors \
  -o none

sleep 8

EXECUTION_NAME="$(az containerapp job execution list \
  --resource-group "$RESOURCE_GROUP" \
  --name "$MIGRATE_JOB" \
  --query "sort_by(@,&properties.startTime)[-1].name" \
  -o tsv)"

if [[ -z "$EXECUTION_NAME" ]]; then
  echo "Could not determine latest job execution name." >&2
  exit 1
fi

echo "Execution: $EXECUTION_NAME"
echo "Waiting for completion..."

elapsed=0
timeout=900

while true; do
  status="$(az containerapp job execution show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$MIGRATE_JOB" \
    --job-execution-name "$EXECUTION_NAME" \
    --query "properties.status" \
    -o tsv 2>/dev/null || echo Unknown)"

  echo "  status=$status elapsed=${elapsed}s"

  case "$status" in
    Succeeded)
      echo
      echo "Reset job succeeded."
      echo
      echo "Logs:"
      az containerapp job logs show \
        --resource-group "$RESOURCE_GROUP" \
        --name "$MIGRATE_JOB" \
        --job-execution-name "$EXECUTION_NAME" \
        --tail 200 2>/dev/null || true

      echo
      echo "Try login:"
      echo "  admin   / $DEMO_ADMIN_PASSWORD"
      echo "  curator / $DEMO_CURATOR_PASSWORD"
      echo "  analyst / $DEMO_ANALYST_PASSWORD"
      echo "  user    / $DEMO_USER_PASSWORD"
      exit 0
      ;;
    Failed|Error)
      echo
      echo "Reset job failed."
      echo
      echo "Execution details:"
      az containerapp job execution show \
        --resource-group "$RESOURCE_GROUP" \
        --name "$MIGRATE_JOB" \
        --job-execution-name "$EXECUTION_NAME" \
        -o jsonc || true

      echo
      echo "Logs:"
      az containerapp job logs show \
        --resource-group "$RESOURCE_GROUP" \
        --name "$MIGRATE_JOB" \
        --job-execution-name "$EXECUTION_NAME" \
        --tail 300 2>/dev/null || true

      exit 1
      ;;
  esac

  if [[ "$elapsed" -ge "$timeout" ]]; then
    echo
    echo "Timeout waiting for reset job."
    echo "Inspect manually:"
    echo "  az containerapp job execution show -g \"$RESOURCE_GROUP\" -n \"$MIGRATE_JOB\" --job-execution-name \"$EXECUTION_NAME\" -o jsonc"
    echo "  az containerapp job logs show -g \"$RESOURCE_GROUP\" -n \"$MIGRATE_JOB\" --job-execution-name \"$EXECUTION_NAME\" --tail 300"
    exit 1
  fi

  sleep 10
  elapsed=$((elapsed + 10))
done
