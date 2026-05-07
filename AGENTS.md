# AGENTS.md

## Dev Startup

```bash
# 1. Start LM Studio on host (port 1234), load a model
# 2. Copy .env.example to .env
# 3. Bring up the Docker stack:
./scripts/dev-up.sh
```

`./scripts/dev-up.sh` runs: postgres + qdrant → alembic migrate → init_db (seed users) → api + frontend.

To restart only the API after code changes:
```bash
docker compose restart api
```

## Key URLs (dev)

- Frontend: http://127.0.0.1:8080/
- API: http://127.0.0.1:8000/
- API docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

## Tests

Backend tests run against **SQLite in-memory** — no postgres or qdrant needed on the host:
```bash
pytest
```

Frontend tests use **vitest + happy-dom**:
```bash
cd frontend && npm test
```

## Database Migrations

```bash
docker compose --profile tools run --rm migrate
```

Alembic reads `DATABASE_URL` from env first, falls back to `alembic.ini`. Docker compose overrides it to point at the `postgres` container.

One migration file: `alembic/versions/20260402_0001_baseline.py`.

## Python Version

Host: `3.12.12` (`.python-version`). Docker image: `3.11-slim`. Both work; the code is 3.11+ compatible.

## LLM Configuration

- Default model: `qwen/qwen3.5-2b` (text + vision, via LM Studio)
- Host app uses `LLM_BASE_URL`; Docker containers use `DOCKER_LLM_BASE_URL` (defaults to `http://host.docker.internal:1234/v1`)
- Config accepts env aliases: `LLM_BASE_URL` / `OPENAI_BASE_URL` / `OLLAMA_URL`; same pattern for API key and model names (`app/config.py`)
- If using a vision-incapable model, set `VISION_ANSWER_ENABLED=false` and `VISION_EXTRACT_ON_INGEST=false`

## Evidence Storage

Artifacts (screenshots, DOM snapshots) go to `./data/evidence/` on the host (mounted into the `api` container).

## Compliance

`COMPLIANCE_ENFORCEMENT=false` (default): Dev Mode bypasses confirmation. API still records the bypass in audit logs. Set `true` to require explicit user confirmation for ingest/query actions. Runtime toggle via `PUT /api/compliance/mode` (admin role).

## Default Users (seeded by init_db)

| Username | Password    | Role    |
|----------|-------------|---------|
| admin    | admin123    | Admin   |
| curator  | curator123  | Curator |
| analyst  | analyst123  | Analyst |
| user     | user123     | User    |

## Architecture

- **API entrypoint**: `app.main:app` (uvicorn)
- **Frontend**: Vue 3 + Vuetify + Pinia + vue-router. Vite dev server proxies `/api` → `http://127.0.0.1:8000`. Production: nginx proxies `/api/` → `api:8000`.
- **Frontend mock mode**: `VITE_USE_MOCK=true` (`.env.development`) intercepts API calls with mock data — no backend needed for frontend-only dev.
- **Ingest pipeline**: `app/services/ingest.py` with fallback strategy `HTML → RENDERED_DOM → SCREENSHOT`. OCR via tesseract; vision extraction via LLM when enabled.
- **Retrieval**: Qdrant for vector search; `sentence-transformers/all-MiniLM-L6-v2` for embeddings. Re-ranking deduplicates by document.
- **Auth**: JWT access + refresh tokens. Refresh tokens are hashed and stored in DB; reuse detection revokes the token family.
- **Request correlation**: `X-Request-ID` header propagated through middleware and audit logs.

## No lint/typecheck tooling

No `ruff`, `mypy`, or pre-commit hooks configured. Python code style is conventional.
