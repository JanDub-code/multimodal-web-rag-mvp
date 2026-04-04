# Local Multimodal MVP

Lokální MVP pro ingest webových stránek a dotazování ve dvou režimech:
- `rag`: retrieval z Qdrantu + odpověď s citacemi
- `no-rag`: přímé volání LLM bez retrieval kroku

Stav README odpovídá aktuální implementaci v repu (kód + `Architektura_systemu_2026-04-02.md` + `TODO.md`).

## 1) Aktuální architektonická realita

- jedna hlavní FastAPI aplikace (`api`) s UI stránkami `/` a `/query`
- PostgreSQL jako source of truth pro metadata, auth, audit, ingest a incidenty
- Qdrant pro embeddingy a retrieval
- evidence artefakty ukládané do `./data/evidence` (bind mount do `api` kontejneru)
- Ollama jako volitelný inference backend (externí host nebo compose služba s profilem `ollama`)
- Alembic migrace přes compose službu `migrate` (profil `tools`)

## 2) Co je implementováno

- ingest URL do KB s fallback strategií `HTML -> RENDERED_DOM -> SCREENSHOT`
- OCR doplnění textu ze screenshotu (Tesseract; při nedostupnosti fallback přes vision model)
- volitelná vision extrakce při ingestu (`VISION_EXTRACT_ON_INGEST=true`) do sekcí/tabulek
- canonical dokument, chunking (`text` + `table`) a embeddingy do Qdrantu
- `rag`/`no-rag` query flow
- retrieval threshold + heuristický lexical reranking + deduplikace podle `doc_id`/`url`
- citace navázané na `source_id`, `doc_id`, `chunk_id`, `chunk_type` + evidence metadata
- lokální auth + RBAC + refresh token rotace + logout revoke
- audit log včetně explicitního eventu `model.call`
- incident flow (`captcha`, `fetch_error`, `render_error`, `parse_error`, `policy_error`, `ingest_failure`)
- request correlation přes `X-Request-ID` (echo do response, propagace do auditu/incident metadata)

## 3) Runtime režimy

### Default (`./scripts/dev-up.sh`)

Spouští stack:
- `postgres`
- `qdrant`
- `migrate` (jednorázově)
- seed default userů
- `api`
- `frontend` (nginx reverzní proxy)

Ollama je v tomto režimu externí/volitelná (`DOCKER_OLLAMA_URL` defaultuje na `http://host.docker.internal:11434`).

### S lokální Ollamou (`./scripts/dev-up.sh --with-ollama`)

Stejné jako default, navíc:
- `ollama` (compose profil `ollama`)

V tomto režimu `DOCKER_OLLAMA_URL` defaultuje na `http://ollama:11434`.

## 4) One-command lokální start

```bash
cp .env.example .env
./scripts/dev-up.sh
# nebo:
./scripts/dev-up.sh --with-ollama
```

Po startu:
- `http://127.0.0.1:8080/` (Ingest UI)
- `http://127.0.0.1:8080/query` (Query UI)
- `http://127.0.0.1:8000/docs` (OpenAPI)
- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/health/ready`

## 5) Databáze a seed

- Schéma je řízené výhradně migracemi v `alembic/versions`.
- `scripts/init_db.py` pouze seeduje default uživatele a kontroluje, že migrace už proběhly.

Ruční migrace:

```bash
alembic upgrade head
```

## 6) Health a readiness

- `GET /health` i `GET /health/ready` aktuálně používají stejnou kontrolu required komponent:
  - required: `postgres`, `qdrant`
  - optional: `ollama`
- návratové kódy:
  - `200`, když required komponenty běží
  - `503`, když některá required komponenta neběží

## 7) Auth, role, endpointy

### Default uživatelé

| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | `Admin` |
| `curator` | `curator123` | `Curator` |
| `analyst` | `analyst123` | `Analyst` |
| `user` | `user123` | `User` |

### Auth endpointy

- `POST /api/auth/login` (OAuth2 form data) -> `access_token` + `refresh_token`
- `POST /api/auth/refresh` -> rotace refresh tokenu + nový access token
- `POST /api/auth/logout` -> revoke refresh tokenu

### Ingest/Query endpointy

- `GET /api/ingest/sources` -> `Admin|Curator|Analyst|User`
- `POST /api/ingest/sources` -> `Admin|Curator`
- `POST /api/ingest/run` -> `Admin|Curator`
- `POST /api/query/` -> `Admin|Curator|Analyst|User`

Validace:
- ingest URL musí zůstat v scope `source.base_url` (origin + path prefix)
- `permission_type` je povinné
- když `permission_type != public`, je povinné `permission_ref`

## 8) Klíčová konfigurace

| Variable | Default | Význam |
|---|---|---|
| `APP_SECRET_KEY` | `change-me-in-production` | JWT secret (vlastní hodnota je povinná mimo dev) |
| `DATABASE_URL` | `postgresql+psycopg://app:app@localhost:5432/multimodal_mvp` | DB URL pro non-docker běh |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant URL pro non-docker běh |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama endpoint |
| `DOCKER_OLLAMA_URL` | prázdné | docker override (`http://ollama:11434` nebo `http://host.docker.internal:11434`) |
| `OLLAMA_MODEL` | `llama3.2:3b` | textový model |
| `OLLAMA_VISION_MODEL` | prázdné | multimodální model |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | embedding model |
| `RETRIEVAL_MIN_SCORE` | `0.25` | minimální score pro kandidáty |
| `QUALITY_THRESHOLD_CHARS` | `300` | hranice pro fallback na render/screenshot |
| `VISION_ANSWER_ENABLED` | `false` | při `rag` připojí relevantní screenshoty do LLM callu |
| `VISION_EXTRACT_ON_INGEST` | `false` | structured vision extrakce při ingestu |
| `FETCH_VERIFY_SSL` | `true` | SSL verifikace při fetchi |

## 9) Testy

`tests/test_smoke.py` pokrývá hlavní tok:
- ingest fallbacky (`HTML`, `RENDERED_DOM`, `SCREENSHOT`) + OCR/vision větve
- CAPTCHA a ingest incident flow
- RAG/no-RAG query
- retrieval threshold + rerank/dedup
- health + readiness endpointy
- request ID echo
- login/refresh/logout token flow

Spuštění:

```bash
pytest
```

## 10) Aktuální limity MVP

- ingest je synchronní (bez worker queue)
- retrieval je Qdrant vector search + lehký heuristický reranking (zatím bez model-based rerankeru)
- bez dostupné Ollamy endpoint vrací fallback text místo modelové odpovědi
- permission metadata zatím nejsou promítnuté do retrieval filtru
- bez `redis`/worker vrstvy není async orchestrace ingestu
- frontend je zatím minimální (2 stránky), rozsáhlejší UX je v TODO (`P1.7`)

## 11) Související dokumenty

- architektura: `Architektura_systemu_2026-04-02.md`
- backlog/provozní stav: `TODO.md`
- doporučení k modelům: `VYBER_MODELU_QWEN35.md`
