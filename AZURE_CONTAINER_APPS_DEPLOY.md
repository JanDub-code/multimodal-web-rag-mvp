# Azure Container Apps deployment — scale to zero containers

This deploys the whole stack as containers in Azure Container Apps:

- `PREFIX-postgres` — Postgres 16 container, internal TCP ingress, Azure Files volume
- `PREFIX-qdrant` — Qdrant container, internal HTTP ingress, Azure Files volume
- `PREFIX-api` — FastAPI container, internal HTTP ingress, Azure Files volumes for evidence/cache
- `PREFIX-frontend` — Nginx/Vue container, public HTTPS ingress
- `PREFIX-migrate` — manual Container Apps Job for Alembic migrations

Default target from your portal screenshot:

```bash
RESOURCE_GROUP=rg-xdub-2220
LOCATION=westus2
PREFIX=xdubrag
```

## First deployment

```bash
az login
export RESOURCE_GROUP=rg-xdub-2220
export LOCATION=westus2
export PREFIX=xdubrag

# Optional, if generation calls should work:
export OPENCODE_API_KEY='...'

./scripts/azure-deploy.sh
```

The script creates/uses ACR, builds the three custom images, deploys the infrastructure, and writes `.azure-deploy.env`.

By default it tries `az acr build` (ACR Tasks). If your subscription blocks ACR Tasks (common on Azure for Students), it automatically falls back to local `docker build` + `docker push`.

You can force behavior:

```bash
export ACR_BUILD_MODE=auto   # default
export ACR_BUILD_MODE=remote # only az acr build
export ACR_BUILD_MODE=local  # only local docker build/push
```

`.azure-deploy.env` contains generated secrets and demo user passwords. It is reused by later deploys so a redeploy does **not** accidentally rotate the Postgres password behind the existing Azure Files data volume. Keep this file private; it is ignored by Git and Docker build context.

## Start when needed

```bash
./scripts/azure-start.sh
```

This sets `minReplicas=1` for Postgres, Qdrant, API, and frontend, runs the migration/seed job, then prints the public frontend URL and demo credentials.

The migration job runs:

1. wait until Postgres accepts connections
2. `alembic upgrade head`
3. seed/update demo users (`admin`, `curator`, `analyst`, `user`)

If you want fixed demo passwords, export them **before** `azure-deploy.sh`:

```bash
export DEMO_ADMIN_PASSWORD='...'
export DEMO_CURATOR_PASSWORD='...'
export DEMO_ANALYST_PASSWORD='...'
export DEMO_USER_PASSWORD='...'
```

To skip demo users entirely:

```bash
export SEED_DEMO_USERS=false
```

## Stop / scale to zero

```bash
./scripts/azure-stop.sh
```

This sets `minReplicas=0` for every long-running container app. Azure Files, ACR, Log Analytics, and the Container Apps environment remain provisioned.

## Rebuild after code changes

```bash
./scripts/azure-rebuild.sh
./scripts/azure-start.sh
```

## Portal controls

In Azure Portal, open each Container App → **Scale** → **Edit and deploy**:

- stopped: minimum replicas `0`
- running: minimum replicas `1`
- maximum replicas `1` for cheapest predictable dev mode

## Important limitation

This is a dev/MVP setup because Postgres and Qdrant are stateful containers on Azure Files. It satisfies “everything is containers” and “scale to zero”, but for production use Azure Database for PostgreSQL and a managed vector store or AKS/stateful storage.
