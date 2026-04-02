# Local Multimodal MVP

Jednoduché lokální MVP pro ingest webových stránek a dotazování nad nimi ve dvou režimech:
- `rag` = retrieval z Qdrantu + odpověď s citacemi
- `no-rag` = přímý dotaz na LLM bez retrieval kroku

Repo je záměrně malé. Fokus je na použitelný local Docker run a provozní minimum, ne na velký refactor architektury.

## 1) Co projekt umí

- ingest URL do znalostní báze
- fallback strategie `HTML -> RENDERED_DOM -> SCREENSHOT`
- OCR doplnění textu ze screenshotu, když je DOM slabý
- volitelná vision extrakce ze screenshotu do strukturovaných sekcí a tabulek
- multimodální answer fáze: při `rag` může LLM dostat i relevantní screenshoty
- canonical document + chunking + embeddings
- Qdrant retrieval se score thresholdem
- režimy `rag` a `no-rag`
- lokální auth, RBAC, audit log
- refresh token flow (DB-backed, rotace, logout revoke)
- jednoduchá CAPTCHA heuristika + incident

## 2) Runtime profily

### `core` (doporučený default)

Služby:
- `api`
- `postgres`
- `qdrant`

LLM backend (Ollama) je v tomto režimu volitelný/external. API běží i bez něj, ale LLM odpovědi nebudou dostupné.

### `core + ollama`

Stejné jako `core`, navíc kontejner:
- `ollama`

## 3) One-command local run

Zkopíruj env:

```bash
cp .env.example .env
```

Spuštění `core`:

```bash
./scripts/dev-up.sh
```

Spuštění `core + ollama`:

```bash
./scripts/dev-up.sh --with-ollama
```

Script dělá:
1. start infrastruktury,
2. explicitní `alembic upgrade head`,
3. seed default userů (`python -m scripts.init_db`),
4. start API.

Open:
- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/query`
- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/health`

## 4) DB migrace

Schéma je řízené přes Alembic:

```bash
alembic upgrade head
```

`scripts/init_db.py` už jen seeduje default uživatele. Schéma se nevytváří přes `create_all`.

## 5) Health a request ID

- `GET /health` kontroluje `postgres` + `qdrant` jako required komponenty.
- `ollama` je reportovaná jako optional komponenta.
- Endpoint vrací:
  - `200`, když required komponenty běží,
  - `503`, když některá required komponenta neběží.
- API podporuje `X-Request-ID`:
  - pokud přijde v requestu, vrací se stejná hodnota v response,
  - pokud chybí, API ji vygeneruje,
  - request ID se propisuje do auditu.

## 6) Default uživatelé

| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | Admin |
| `curator` | `curator123` | Curator |
| `analyst` | `analyst123` | Analyst |
| `user` | `user123` | User |

## 7) Důležité endpointy a role

### Auth

- `POST /api/auth/login` -> vrací `access_token` + `refresh_token`
- `POST /api/auth/refresh` -> rotate refresh token + nový access token
- `POST /api/auth/logout` -> revoke refresh token

### Ingest / Query

- `GET /api/ingest/sources` -> všechny role
- `POST /api/ingest/sources` -> `Admin`, `Curator`
- `POST /api/ingest/run` -> `Admin`, `Curator`
- `POST /api/query/` -> všechny role

`POST /api/ingest/run` validuje, že URL zůstává v scope `source.base_url`.

## 8) Důležitá konfigurace

| Variable | Default | Meaning |
|---|---|---|
| `APP_SECRET_KEY` | `change-me` | JWT secret, změň |
| `DATABASE_URL` | `postgresql+psycopg://app:app@localhost:5432/multimodal_mvp` | DB URL pro non-docker run |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant URL pro non-docker run |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama URL |
| `DOCKER_OLLAMA_URL` | prázdné | docker override pro API/migrate (`http://ollama:11434` nebo `http://host.docker.internal:11434`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_MINUTES` | `43200` | Refresh token TTL |
| `OLLAMA_MODEL` | `llama3.2:3b` | textový model |
| `OLLAMA_VISION_MODEL` | prázdné | multimodální model |
| `VISION_ANSWER_ENABLED` | `false` | při `rag` pošle screenshoty i do LLM |
| `VISION_EXTRACT_ON_INGEST` | `false` | structured vision extrakce při ingestu |
| `RETRIEVAL_MIN_SCORE` | `0.25` | minimální relevance hitu |
| `QUALITY_THRESHOLD_CHARS` | `300` | hranice pro render fallback |

## 9) Testy

Smoke testy pokrývají:
- ingest fallbacky (HTML/RENDERED_DOM/SCREENSHOT),
- CAPTCHA incident flow,
- RAG/no-RAG query flow,
- retrieval threshold + rerank,
- health endpoint chování,
- request ID echo,
- refresh token rotaci a logout revoke.

Spuštění:

```bash
pytest
```

## 10) Aktuální limity MVP

- ingest je synchronní
- retrieval je čistě vektorový (Qdrant)
- bez běžící Ollamy nejsou LLM odpovědi dostupné
- permission metadata zatím nejsou promítnuté do retrieval filtru
- bez workers/redis není async job orchestrace

## 11) Výběr modelu

Doporučení k rodině Qwen3.5 je v souboru:
- `VYBER_MODELU_QWEN35.md`
