# AGENTS.md

## Dev Startup

```bash
# 1. Start LM Studio separately on host (port 1234), load a model
# 2. Then bring up the Docker stack:
./scripts/dev-up.sh
```

`./scripts/dev-up.sh` starts: postgres → migrate (alembic) → init_db → api + frontend.

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

Backend (pytest, runs against SQLite in-memory):
```bash
pytest
```

Frontend (vitest):
```bash
cd frontend && npm test
```

## Database Migrations

```bash
docker compose --profile tools run --rm migrate
```

## Python Version

`3.12.12` (see `.python-version`). Docker image uses `3.11-slim`.

## LLM Configuration

- Default model: `qwen/qwen3.5-2b` (text + vision, via LM Studio at `http://127.0.0.1:1234/v1`)
- Host app uses `LLM_BASE_URL`; Docker containers use `DOCKER_LLM_BASE_URL` (defaults to `http://host.docker.internal:1234/v1`)
- If using a vision-incapable model, set `VISION_ANSWER_ENABLED=false` and `VISION_EXTRACT_ON_INGEST=false`

## Evidence Storage

Artifacts (screenshots, DOM snapshots) go to `./data/evidence/` on the host (mounted into the `api` container).

## Compliance

`COMPLIANCE_ENFORCEMENT=false` (default): Dev Mode bypasses confirmation. API still records the bypass in audit logs. Set to `true` to require explicit user confirmation for ingest/query actions.

## No lint/typecheck tooling

This repo has no `ruff`, `mypy`, or pre-commit hooks configured. Python code style is conventional.
