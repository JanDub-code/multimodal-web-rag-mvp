# LM Studio Setup

Tento projekt je ted nastaveny na OpenAI-compatible backend s defaultem pro LM Studio.
Vychozi textovy model v projektu je `qwen/qwen3.5-2b`.

## 1. Co musi bezet

- LM Studio s aktivnim Local Serverem
- model `qwen/qwen3.5-2b`
- pokud chces vision funkce, tak i samostatny multimodalni model pro `LLM_VISION_MODEL`

## 2. Overeni LM Studio API

Na host stroji musi fungovat:

```bash
curl http://127.0.0.1:1234/v1/models
```

Ocekavany vysledek je seznam modelu, kde je mimo jine `qwen/qwen3.5-2b`.

Rychly test odpovedi modelu:

```bash
curl http://127.0.0.1:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen/qwen3.5-2b","messages":[{"role":"user","content":"Napis jednu kratkou vetu cesky."}]}'
```

Na Windows PowerShell pouzij escapovani podle shellu, ale endpoint zustava stejny: `POST /v1/chat/completions`.

## 3. Konfigurace projektu

Zkopiruj sablonu env:

```bash
cp .env.example .env
```

Pak v `.env` nastav minimalne toto:

```env
LLM_BASE_URL=http://127.0.0.1:1234/v1
LLM_API_KEY=lm-studio
LLM_MODEL=qwen/qwen3.5-2b
LLM_VISION_MODEL=
VISION_ANSWER_ENABLED=false
VISION_EXTRACT_ON_INGEST=false
```

Poznamky:
- `LLM_API_KEY` muze byt klidne jen placeholder `lm-studio`, pokud v LM Studio nemas zapnutou auth.
- `LLM_VISION_MODEL` nech prazdny, pokud aktualni model neumi obrazovy vstup.
- Vision feature zapinej az ve chvili, kdy mas nahrany skutecny multimodalni model.

## 4. Docker runtime

Aplikace v Dockeru musi na LM Studio bezici na hostu mluvit pres:

```env
DOCKER_LLM_BASE_URL=http://host.docker.internal:1234/v1
```

To je uz vychozi hodnota v `scripts/dev-up.sh`, takze ji vetsinou nemusis menit.

## 5. Start aplikace

```bash
./scripts/dev-up.sh
```

Script spusti:
- PostgreSQL
- Qdrant
- migrace
- API
- frontend

LM Studio se nestartuje z Docker Compose. Musi bezet separatne.

## 6. Co se v projektu zmenilo

- projekt uz nepouziva `OLLAMA_*` konfiguraci jako hlavni cestu
- modelove volani jdou pres OpenAI-compatible `POST /v1/chat/completions`
- healthcheck kontroluje `GET /v1/models`
- Docker Compose uz nestartuje vlastni `ollama` service

## 7. Vision rezim

Pokud chces zpracovavat screenshoty pres LLM, nastav multimodalni model:

```env
LLM_VISION_MODEL=sem_dopln_multimodalni_model
VISION_ANSWER_ENABLED=true
VISION_EXTRACT_ON_INGEST=true
```

Pokud pouzijes textovy model bez vision podpory a tyto volby zapnes, volani s obrazkem muze selhat na 4xx chybe z backendu.

## 8. Troubleshooting

### `/health` ukazuje `llm: down`

Zkontroluj:
- bezi LM Studio Local Server
- funguje `curl http://127.0.0.1:1234/v1/models`
- `LLM_BASE_URL` nebo `DOCKER_LLM_BASE_URL` nema navic segment typu `/get/v1`

### API vraci fallback text misto odpovedi modelu

Zkontroluj:
- `LLM_MODEL` presne odpovida `id` z `/v1/models`
- LM Studio ma model opravdu nacteny, nejen stazeny
- pokud bezis API v Dockeru, pouzivas `host.docker.internal`, ne `127.0.0.1`

### Volani s obrazkem pada

Zkontroluj:
- je nastaveny `LLM_VISION_MODEL`
- vybrany model umi multimodalni vstup
- `VISION_ANSWER_ENABLED` a `VISION_EXTRACT_ON_INGEST` nejsou omylem zapnute s textovym modelem
