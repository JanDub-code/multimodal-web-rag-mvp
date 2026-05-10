# Local Multimodal MVP

Lokalni MVP pro ingest webovych stranek a dotazovani ve dvou rezimech:

- `rag`: vektorovy retrieval z Qdrantu + odpoved pres OpenCode
- `no-rag`: prime volani vybraneho OpenCode modelu bez retrieval kroku

V runtime uz neni Ollama, vlastni gateway ani lokalni `opencode serve`. Generovani odpovedi jde primo z FastAPI backendu na OpenCode Go API, backend proto potrebuje `OPENCODE_API_KEY`. RAG retrieval pouziva lokalni CPU embedding pres FastEmbed/ONNX a uklada vektory do Qdrantu.

## Architektura

- FastAPI aplikace (`api`)
- Vue frontend (`frontend`)
- PostgreSQL pro metadata, auth, audit, ingest, incidenty, dokumenty a chunky
- Qdrant pro vektorovy index
- evidence artefakty v `./data/evidence`
- OpenCode Go API pro generovani textu a vision fallback
- FastEmbed CPU model `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` pro RAG embeddingy

## Modely v chatu

UI nabizi pro RAG i no-RAG:

- `DeepSeek V4 Flash`
- `MiniMax M2.7`
- `MiniMax M2.5`
- `Kimi K2.5 Vision`

Backend povoluje pouze modely s prefixem `opencode-go/` a vola Go endpoint (`OPENCODE_GO_BASE_URL`).

Pokud jsou k odpovedi pripojene screenshoty, backend pouzije `VISION_GENERATION_MODEL` a vola Go endpoint (vision fallback).

## Konfigurace

Minimalni `.env`:

```env
APP_NAME=Local Multimodal MVP
APP_HOST=127.0.0.1
APP_PORT=8000
APP_SECRET_KEY=change-me-in-production

DATABASE_URL=postgresql+psycopg://app:app@localhost:5432/multimodal_mvp
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=chunks_fastembed_multilingual_minilm_384

EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
EMBEDDING_DIMENSIONS=384
DEFAULT_GENERATION_MODEL=opencode-go/deepseek-v4-flash
VISION_GENERATION_MODEL=opencode-go/kimi-k2.5
GENERATION_PROVIDER=opencode_go
OPENCODE_GO_BASE_URL=https://opencode.ai/zen/go/v1
OPENCODE_API_KEY=

VISION_EXTRACT_ON_INGEST=false
VISION_MAX_IMAGES=2
VISION_TIMEOUT_SECONDS=90
VISION_PROMPT_MAX_CONTEXT_CHARS=3000
FETCH_VERIFY_SSL=true

EVIDENCE_DIR=./data/evidence
SCREENSHOT_DIR=./data/evidence/screenshots
DOM_SNAPSHOT_DIR=./data/evidence/dom

ACCESS_TOKEN_EXPIRE_MINUTES=480
REFRESH_TOKEN_EXPIRE_MINUTES=43200
QUALITY_THRESHOLD_CHARS=300
RETRIEVAL_MIN_SCORE=0.25
COMPLIANCE_ENFORCEMENT=false
```

Pred realnym dotazovanim nastav na backendu `OPENCODE_API_KEY`. Lokalni `opencode serve` se nepouziva.

Pro Docker Compose muzes drzet secret mimo repo a predat ho pri startu:

```bash
OPENCODE_API_KEY='sk-...' ./scripts/dev-up.sh
```

Alternativne muzes pouzit runtime override:

```bash
OPENCODE_API_KEY_RUNTIME='sk-...' ./scripts/dev-up.sh
```

V kontejneru ma runtime override prednost pred hodnotou z `.env`, takze lokalni soubor zustava jen jako fallback.

## Start

```bash
./scripts/dev-up.sh
```

Oteviraci URL:

- frontend: `http://127.0.0.1:8080`
- API: `http://127.0.0.1:8000`
- health: `http://127.0.0.1:8000/health`

Docker stack spousti jen:

- `postgres`
- `qdrant`
- `migrate`
- `api`
- `frontend`

## RAG embedding

RAG vola lokalni CPU embedding model pres FastEmbed. Nejde pres Ollamu. Pri ingestu se chunky embednou do Qdrantu, pri dotazu se embedne query stejnym modelem a vybrane chunky se poslou do OpenCode modelu jako kontext.

Vychozi model je `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, 384 dimenzi. Je to kompromis: dost maly na CPU, porad pouzitelny pro CZ/EN retrieval.

## Runtime API

- `GET /api/runtime/models` vrati aktualni mapovani modelu a retrieval vrstvy.
- `GET /api/query/models` vrati modely dostupne v chat UI.
- `POST /api/query/` podporuje `mode`, `top_k`, `model` a `conversation_history`.
- `POST /api/ingest/run` uklada canonical dokument a chunky do PostgreSQL.

Podrobne rozhodnuti a tok pres OpenCode Go je v `OPENCODE_GO_ARCHITECTURE.md`.
