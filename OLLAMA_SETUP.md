# Ollama Setup

Tento projekt je nastaveny na Ollamu pro text, vision i embedding volani.
Text a vision pouzivaji Ollama `/api/chat`.
Embeddingy pouzivaji nativni Ollama endpoint `/api/embed`.

Vychozi textovy model v projektu je `qwen3.5:2b`.
Vychozi vision model v projektu je `qwen3.5:2b`.
Vychozi embedding model je `qwen3-embedding:8b`.

## 1. Co musi bezet

- Ollama server na `http://127.0.0.1:11434`
- model `qwen3.5:2b`
- model `qwen3-embedding:8b`

## 2. Priprava Ollamy

```bash
ollama serve
ollama pull qwen3.5:2b
ollama pull qwen3-embedding:8b
```

## 3. Overeni API

Na host stroji musi fungovat:

```bash
curl http://127.0.0.1:11434/api/tags
```

Rychly test odpovedi modelu:

```bash
curl http://127.0.0.1:11434/api/chat \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3.5:2b","messages":[{"role":"user","content":"Napis jednu kratkou vetu cesky."}],"stream":false}'
```

Rychly test embeddingu:

```bash
curl http://127.0.0.1:11434/api/embed \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3-embedding:8b","input":["kratky test"]}'
```

## 4. Konfigurace projektu

Zkopiruj sablonu env:

```bash
cp .env.example .env
```

Minimalni nastaveni:

```env
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3.5:2b
OLLAMA_VISION_MODEL=qwen3.5:2b
EMBEDDING_BASE_URL=http://127.0.0.1:11434
EMBEDDING_MODEL=qwen3-embedding:8b
EMBEDDING_DIMENSIONS=4096
QDRANT_COLLECTION=chunks_qwen3_embedding_8b_4096
VISION_ANSWER_ENABLED=true
VISION_EXTRACT_ON_INGEST=true
```

Poznamky:
- Pokud nechces pouzivat vision, nastav `VISION_ANSWER_ENABLED=false`, `VISION_EXTRACT_ON_INGEST=false` a `OLLAMA_VISION_MODEL` vymaz.

## 5. Docker runtime

Aplikace v Dockeru mluvi na Ollamu bezici na hostu pres:

```env
DOCKER_OLLAMA_BASE_URL=http://host.docker.internal:11434
DOCKER_EMBEDDING_BASE_URL=http://host.docker.internal:11434
```

To je vychozi hodnota v `scripts/dev-up.sh`, takze ji vetsinou nemusis menit.

## 6. Start aplikace

```bash
./scripts/dev-up.sh
```

Script spusti:
- PostgreSQL
- Qdrant
- migrace
- API
- frontend

Ollama se nestartuje z Docker Compose. Musi bezet separatne.

## 7. Troubleshooting

### `/health` ukazuje `ollama: down`

Zkontroluj:
- bezi Ollama
- funguje `curl http://127.0.0.1:11434/api/tags`
- `OLLAMA_BASE_URL` nebo `DOCKER_OLLAMA_BASE_URL` obsahuje jen zakladni URL bez cesty

### API vraci fallback text misto odpovedi modelu

Zkontroluj:
- `OLLAMA_MODEL` presne odpovida tagu z `ollama list`
- model je stazeny pres `ollama pull`
- pokud bezis API v Dockeru, pouzivas `host.docker.internal`, ne `127.0.0.1`

### Volani s obrazkem pada

Zkontroluj:
- je nastaveny `OLLAMA_VISION_MODEL`
- vybrany model umi multimodalni vstup
- `VISION_ANSWER_ENABLED` a `VISION_EXTRACT_ON_INGEST` nejsou omylem zapnute s textovym modelem
