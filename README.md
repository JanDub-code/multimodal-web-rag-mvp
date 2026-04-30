# Local Multimodal MVP

Lokalni MVP pro ingest webovych stranek a dotazovani ve dvou rezimech:
- `rag`: retrieval z Qdrantu + odpoved s citacemi
- `no-rag`: prime volani LLM bez retrieval kroku

Aktualni inference backend pro text a vision je OpenAI-compatible API. Vychozi lokalni cil je LM Studio na `http://127.0.0.1:1234/v1` s textovym i vision modelem `qwen/qwen3.5-2b`.

Embedding backend je samostatna Ollama instance na `http://127.0.0.1:11434` s default modelem `qwen3-embedding:8b`.

## Architektonicka realita

- FastAPI aplikace (`api`) s UI strankami `/` a `/query`
- PostgreSQL pro metadata, auth, audit, ingest a incidenty
- Qdrant pro embeddingy a retrieval
- evidence artefakty v `./data/evidence`
- LM Studio nebo jiny OpenAI-compatible backend jako text/vision inference vrstva
- Ollama jako embedding backend
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
2. Spust Ollamu a stahni embedding model:
   ```bash
   ollama serve
   ollama pull qwen3-embedding:8b
   ```
3. Zkopiruj `.env.example` na `.env`.
4. Spust `./scripts/dev-up.sh`.
5. Otevri:
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

LM Studio i Ollama bezi mimo Docker. Kontejner `api` se na hosta pripojuje pres:
- `DOCKER_LLM_BASE_URL`, default `http://host.docker.internal:1234/v1`
- `DOCKER_EMBEDDING_BASE_URL`, default `http://host.docker.internal:11434`

## Klicova konfigurace

- `LLM_BASE_URL`: OpenAI-compatible base URL pro lokalni beh mimo Docker
- `DOCKER_LLM_BASE_URL`: stejny endpoint pro kontejnery
- `LLM_API_KEY`: neprazdny placeholder nebo skutecny token z LM Studio
- `LLM_MODEL`: textovy model, default `qwen/qwen3.5-2b`
- `LLM_VISION_MODEL`: multimodalni model pro screenshoty, default `qwen/qwen3.5-2b`
- `EMBEDDING_BASE_URL`: Ollama base URL pro lokalni embedding mimo Docker, default `http://127.0.0.1:11434`
- `DOCKER_EMBEDDING_BASE_URL`: Ollama endpoint pro kontejnery, default `http://host.docker.internal:11434`
- `EMBEDDING_MODEL`: embedding model pro lokalni retrieval, default `qwen3-embedding:8b`
- `EMBEDDING_DIMENSIONS`: pozadovana vystupni dimenze embeddingu, default `4096`
- `QDRANT_COLLECTION`: kolekce pro vektory. Default `chunks_qwen3_embedding_8b_4096`
- `VISION_ANSWER_ENABLED`: pripoji screenshoty do RAG odpovedi, default `true`
- `VISION_EXTRACT_ON_INGEST`: zapne strukturovanou vision extrakci pri ingestu, default `true`
- `COMPLIANCE_ENFORCEMENT`: `false` = Dev Mode bypass (akce bezi, audit nese bypass flag), `true` = API vyzaduje potvrzeni pro `ingest`/`query`

Pokud pouzivas textovy model bez podpory obrazu, vypni vision volby (`VISION_ANSWER_ENABLED=false`, `VISION_EXTRACT_ON_INGEST=false`) a `LLM_VISION_MODEL` nastav prazdne.

Pri zmene `EMBEDDING_MODEL` nebo `EMBEDDING_DIMENSIONS` pouzij novou `QDRANT_COLLECTION` a proved reingest. Aplikace existujici kolekci s jinou dimenzi automaticky nemaze.

## Runtime modely

- `GET /api/runtime/models` (`Admin`): vrati aktualni mapovani modelu na akce.
- `POST /api/query/` vraci `model_usage` pro `no-rag` i `rag`.
- `POST /api/ingest/run` vraci `model_usage` pro embedding a pripadnou vision extrakci.

## Embedding model decision

Porovnane kandidaty pro CZ/EN retrieval pres Ollamu:

| Kandidat | Role | Tradeoff |
|---|---|---|
| `qwen3-embedding:0.6b` | low-resource fallback | nejrychlejsi a nejmensi, ale nizsi rezerva pro narocnejsi multijazycny retrieval |
| `qwen3-embedding:4b` | kompromis | lepsi kvalita nez 0.6B, nizsi pametove naroky nez 8B |
| `qwen3-embedding:8b` | default | nejlepsi kvalita z kandidatu pro CZ/EN a dlouhy kontext, za cenu vyssi RAM/VRAM a latence |

Vychozi volba je `qwen3-embedding:8b`, protoze prioritou MVP je kvalita retrievalu a citaci. Pokud lokalni stroj nestiha ingest/query latenci, nejblizsi fallback je `qwen3-embedding:4b`.

### Benchmark

Benchmark runner pouziva lokalne ingestovane chunky, samostatne Qdrant benchmark kolekce a dotazy z JSON souboru:

```bash
python -m scripts.benchmark_embeddings \
  --queries reports/embedding_eval_queries.json \
  --models qwen3-embedding:0.6b qwen3-embedding:4b qwen3-embedding:8b \
  --top-k 5 \
  --readme-update README.md
```

Format dotazu:

```json
[
  {
    "query": "Jak system uklada evidence artefakty?",
    "expected_url_contains": "example.com/docs/evidence"
  },
  {
    "query": "How are citations linked to retrieved chunks?",
    "expected_doc_id": 12
  }
]
```

<!-- EMBEDDING_BENCHMARK_TABLE_START -->
| Model | Dimenze | Hit@5 | MRR@5 | p50 ms | p95 ms | Model MB | Loaded RAM MB | VRAM MB | CPU % | Poznamka |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `qwen3-embedding:0.6b` | 1024 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | spustit na stroji s Ollamou a lokalne ingestovanymi daty |
| `qwen3-embedding:4b` | 2560 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | spustit na stroji s Ollamou a lokalne ingestovanymi daty |
| `qwen3-embedding:8b` | 4096 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | default pro MVP |
<!-- EMBEDDING_BENCHMARK_TABLE_END -->

## Retrieval eval (Recall@k, MRR@k)

Eval dataset pro CZ/EN dotazy je v `reports/retrieval_eval_dataset.json`. Obsahuje real-world prompty a ocekavana URL/chunky (uprav podle konkretniho knowledge base).

Runner skript `scripts/eval_retrieval.py` meri:
- Recall@k a MRR@k nad aktualni retrieval pipeline (`search_top_k`)
- latenci (p50/p95)

Output se uklada do verzovanych reportu `reports/retrieval_eval_YYYYMMDD_HHMMSS.json`.
V repozitari je ulozen placeholder report `reports/retrieval_eval_2026-04-30.json` pro udrzeni historie (nahrazuje se realnym behy skriptu).

### Quality gate

Minimalni quality gate pro retrieval:
- Recall@5 >= 0.60
- MRR@5 >= 0.30

Skript vraci non-zero exit code, pokud gate neprojde.

## Refresh workflow (re-ingest)

Refresh workflow je explicitne dostupny na `POST /api/ingest/refresh` a pouziva stejny ingest pipeline bez nutnosti rucniho mazani dokumentu.
Metadata pro refresh rozhodovani jsou ulozena na urovni `source_urls` (URL, last_successful_ingest_ts, refresh_interval_minutes).

Automaticky scheduler se spousti pri `REFRESH_SCHEDULER_ENABLED=true` a v intervalech `REFRESH_SCHEDULER_INTERVAL_SECONDS` kontroluje stale URL.
Refresh job je idempotentni (prioritne aktualizuje existujici dokumenty, nezdvojuje chunky) a loguje auditni zaznam `refresh.batch` s pocty URL, uspesnosti a incidenty.

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
