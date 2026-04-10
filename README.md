# Local Multimodal MVP

Lokalni MVP pro ingest webovych stranek a dotazovani ve dvou rezimech:
- `rag`: retrieval z Qdrantu + odpoved s citacemi
- `no-rag`: prime volani LLM bez retrieval kroku

Aktualni inference backend je OpenAI-compatible API. Vychozi lokalni cil je LM Studio na `http://127.0.0.1:1234/v1` s modelem `qwen/qwen3.5-2b`.

## Architektonicka realita

- FastAPI aplikace (`api`) s UI strankami `/` a `/query`
- PostgreSQL pro metadata, auth, audit, ingest a incidenty
- Qdrant pro embeddingy a retrieval
- evidence artefakty v `./data/evidence`
- LM Studio nebo jiny OpenAI-compatible backend jako inference vrstva
- Alembic migrace pres compose sluzbu `migrate`

## Co je implementovano

- ingest URL do KB s fallback strategii `HTML -> RENDERED_DOM -> SCREENSHOT`
- OCR doplneni textu ze screenshotu
- volitelna vision extrakce pri ingestu do sekci a tabulek
- canonical dokument, chunking (`text` + `table`) a embeddingy do Qdrantu
- `rag` a `no-rag` query flow
- compliance enforcement flow (`Dev Mode` bypass vs `Enforcement ON`)
- audit log vcetne eventu `model.call`
- incident flow (`captcha`, `fetch_error`, `render_error`, `parse_error`, `policy_error`, `ingest_failure`)
- request correlation pres `X-Request-ID`

## Quick start

1. V LM Studio zapni Local Server a nacti model `qwen/qwen3.5-2b`.
2. Zkopiruj `.env.example` na `.env`.
3. Spust `./scripts/dev-up.sh`.
4. Otevri:
   - `http://127.0.0.1:8080/`
   - `http://127.0.0.1:8080/query`
   - `http://127.0.0.1:8000/docs`
   - `http://127.0.0.1:8000/health`

Podrobny navod je v `LM_STUDIO_SETUP.md`.

### Prihlaseni (dev)

Login formular obsahuje prepinac uctu:
- `Admin` (plny pristup)
- `Curator` (ingest + zdroje)
- `Analyst` (dotazy + analyza)
- `User` (dotazy)

### Ingest workflow (UI)

1. Otevri `Sprava zdroju` a pridej zdroj.
2. Po ulozeni se muzes rovnou prepnout na `Ingest` (automaticky, nebo pres tlacitko `Run ingest` u zdroje).
3. Na strance `/ingest` zkontroluj predvyplneny zdroj + URL a klikni `Run ingest`.

## Runtime

Docker stack spousti:
- `postgres`
- `qdrant`
- `migrate`
- `api`
- `frontend`

LM Studio bezi mimo Docker. Kontejner `api` se na hosta pripojuje pres `DOCKER_LLM_BASE_URL`, ktere defaultne miri na `http://host.docker.internal:1234/v1`.

## Klicova konfigurace

- `LLM_BASE_URL`: OpenAI-compatible base URL pro lokalni beh mimo Docker
- `DOCKER_LLM_BASE_URL`: stejny endpoint pro kontejnery
- `LLM_API_KEY`: neprazdny placeholder nebo skutecny token z LM Studio
- `LLM_MODEL`: textovy model, default `qwen/qwen3.5-2b`
- `LLM_VISION_MODEL`: volitelny multimodalni model pro screenshoty
- `VISION_ANSWER_ENABLED`: pripoji screenshoty do RAG odpovedi
- `VISION_EXTRACT_ON_INGEST`: zapne strukturovanou vision extrakci pri ingestu
- `EMBEDDING_MODEL`: embedding model pro lokalni retrieval
- `COMPLIANCE_ENFORCEMENT`: `false` = Dev Mode bypass (akce bezi, audit nese bypass flag), `true` = API vyzaduje potvrzeni pro `ingest`/`query`

Pokud pouzivas textovy model bez podpory obrazu, nech `VISION_ANSWER_ENABLED=false`, `VISION_EXTRACT_ON_INGEST=false` a `LLM_VISION_MODEL` prazdny.

## Compliance API

- `GET /api/compliance/mode`: vrati aktualni enforcement rezim.
- `PUT /api/compliance/mode`: prepne enforcement (`admin` role).
- `GET /api/compliance/history`: vrati historii compliance potvrzeni/bypass.
- `POST /api/compliance/confirm`: zapise explicitni potvrzeni/bypass.

`POST /api/query/` a `POST /api/ingest/run` podporuji:
- `operation_id` (volitelne): pokud chybi, backend vytvori fallback a vrati ho v response.
- `compliance_confirmed` (bool), `compliance_reason` (string), `compliance_bypassed` (bool).

## Health a readiness

- required komponenty: `postgres`, `qdrant`
- optional komponenta: `llm`
- `GET /health` a `GET /health/ready` vraci `200`, kdyz bezi required komponenty
- pokud je LM Studio vypnute, API zustane `degraded` jen tehdy, kdyz spadne PostgreSQL nebo Qdrant

## Testy

Spusteni smoke testu:

```bash
pytest
```

## Souvisejici dokumenty

- `LM_STUDIO_SETUP.md`
- `Architektura_systemu_2026-04-02.md`
- `TODO.md`
- `VYBER_MODELU_QWEN35.md`
