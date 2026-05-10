# OpenCode Go architektura

Tento projekt vola OpenCode Go primo z FastAPI backendu. Lokalni `opencode serve` se uz nepouziva.

## Proc

- Frontend nema znat OpenCode API key. Mluvi jen s nasim backendem.
- Backend drzi cele RAG rizeni: FastEmbed vytvori embedding, Qdrant vrati relevantni chunky a az vybrany kontext jde do modelu.
- Odstraneni `opencode serve` zjednodusuje runtime. Neni potreba dalsi lokalni proces, basic auth ani host bridge.
- Model selection, audit, compliance a error handling zustavaji v jednom backend endpointu.
- Vision chovani je explicitni: bezne textove dotazy pouzivaji zvoleny textovy model, odpovedi se screenshoty pouzivaji Kimi K2.5 fallback.

## Co se zmenilo

Runtime tok je:

```text
Vue frontend
  -> FastAPI /api/query/
    -> conversation_history z aktivni session
    -> FastEmbed + Qdrant retrieval pro RAG
    -> prompt s aktualni otazkou, historii a RAG kontextem
    -> OpenCode Go API
```

Pro `no-rag` backend preskoci FastEmbed a Qdrant, ale stale posle aktualni otazku a nedavnou historii konverzace.

## Jak se vola OpenCode Go

Vsechna generace pouziva:

```env
OPENCODE_GO_BASE_URL=https://opencode.ai/zen/go/v1
OPENCODE_API_KEY=
```

Vychozi textovy model:

```env
DEFAULT_GENERATION_MODEL=opencode-go/deepseek-v4-flash
```

Vision fallback:

```env
VISION_GENERATION_MODEL=opencode-go/kimi-k2.5
```

Backend u modelu s prefixem `opencode-go/` pred volanim Go API prefix odrizne.

Pokud jsou k odpovedi pripojene screenshoty, backend pouzije `VISION_GENERATION_MODEL` a vola Go API (Kimi fallback) bez ohledu na vybrany textovy model.

MiniMax modely pouzivaji Go Anthropic-compatible endpoint `/messages`. Ostatni modely pouzivaji Go OpenAI-compatible endpoint `/chat/completions`.

## Modely v UI

Chat nabizi:

- `opencode-go/deepseek-v4-flash`
- `opencode-go/minimax-m2.7`
- `opencode-go/minimax-m2.5`
- `opencode-go/kimi-k2.5`

Pokud ma RAG odpoved screenshot evidence, vybrany model se pro konkretni generacni call prepne na `VISION_GENERATION_MODEL`.

## Historie konverzace

Frontend posila do `/api/query/` pole `conversation_history`.

Limit je schvalne omezeny:

- frontend posle maximalne 12 predchozich zprav
- backend pouzije maximalne 8 poslednich zprav
- backend orezava dlouhy obsah jednotlivych zprav

Historie pomaha s navaznosti chatu. RAG prompt ale stale rika modelu, ze fakticke odpovedi maji byt oprete o dodany kontext a citace.

## Dotcene soubory

- `app/config.py` - OpenCode Go konfigurace, API key a vision fallback model.
- `app/services/multimodal.py` - prime volani OpenCode Go API, OpenAI-compatible a Anthropic-compatible payloady, Kimi fallback pro obrazky.
- `app/services/answering.py` - prompt s historii konverzace, RAG kontextem a audit skutecneho vision modelu.
- `app/services/model_usage.py` - runtime metadata pro text, retrieval a vision fallback.
- `app/api/routes_query.py` - seznam povolenych modelu a `conversation_history` v query requestu.
- `app/main.py` - health endpoint ukazuje OpenCode Go endpoint a stav API key.
- `frontend/src/views/ChatView.vue` - UI model options a posilani historie aktualni session.
- `frontend/src/services/queryService.js` - query payload obsahuje `conversation_history`.
- `.env` - lokalni OpenCode Go konfigurace.
- `.env.example` - vzor OpenCode Go konfigurace.
- `README.md` - strucne narovnani runtime popisu a odkaz na tento dokument.
- `OPENCODE_GO_ARCHITECTURE.md` - tento dokument.
