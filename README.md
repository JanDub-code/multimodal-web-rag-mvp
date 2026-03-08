# Local Multimodal MVP

Jednoduché lokální MVP pro ingest webových stránek a dotazování nad nimi ve dvou režimech:
- `rag` = retrieval z Qdrantu + odpověď s citacemi
- `no-rag` = přímý dotaz na LLM bez retrieval kroku

Projekt je záměrně malý. Dokumentace je proto konsolidovaná do tohoto README a jednoho samostatného souboru k výběru modelu:
- `README.md` = instalace, spuštění, chování aplikace, limity
- `VYBER_MODELU_QWEN35.md` = doporučení modelů pro domácí GPU a školní server / MetaCentrum

## 1) Co projekt umí

- ingest URL do znalostní báze
- fallback strategie `HTML -> RENDERED_DOM -> SCREENSHOT`
- OCR doplnění textu ze screenshotu, když je DOM slabý
- volitelná vision extrakce ze screenshotu do strukturovaných sekcí a tabulek
- multimodální answer fáze: při `rag` může LLM dostat i relevantní screenshoty
- canonical document + chunking + embeddings
- Qdrant retrieval se score thresholdem
- režimy `rag` a `no-rag`
- lokální auth, RBAC a audit log
- jednoduchá CAPTCHA heuristika
- deduplikace při re-ingestu stejné URL

## 2) Použitý stack

- **API / app**: FastAPI
- **LLM odpovědi**: Ollama
- **embeddingy**: `sentence-transformers/all-MiniLM-L6-v2`
- **vektorová DB**: Qdrant
- **relační DB**: PostgreSQL
- **render fallback**: Playwright
- **OCR fallback**: pytesseract
- **volitelná vision vrstva**: Ollama multimodal model (např. Qwen rodina)

Výchozí lokální LLM v `.env`:
- `llama3.2:3b`

## 3) Požadavky

- Windows nebo Linux
- Docker / Docker Desktop
- Python **3.11 nebo 3.12**
- nainstalovaná Ollama
- pro nejlepší OCR fallback je vhodný Tesseract v systému; když chybí a je nastavený vision model v Ollamě, aplikace zkusí vision OCR fallback

## 4) Instalace

### Infrastruktura

```powershell
docker compose up -d postgres qdrant
```

### Python prostředí

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
playwright install chromium
Copy-Item .env.example .env
```

Na Linuxu je možné místo systémového Playwright cache použít lokální projektovou cestu:

```bash
PLAYWRIGHT_BROWSERS_PATH=.playwright-browsers python -m playwright install chromium
```

Pokud PowerShell blokuje aktivaci:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
. .\.venv\Scripts\Activate.ps1
```

### Ollama

```powershell
ollama pull llama3.2:3b
```

Před spuštěním změň v `.env` hodnotu `APP_SECRET_KEY`.

## 5) Spuštění

### Inicializace DB

```powershell
python -m scripts.init_db
```

### Start aplikace

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Nespouštěj `python main.py`. Správný entrypoint je `uvicorn app.main:app`.

Aplikace po startu kontroluje:
- embedding model
- Qdrant
- PostgreSQL
- Ollamu

Open:
- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/query`
- `http://127.0.0.1:8000/docs`

## 6) Default uživatelé

| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | Admin |
| `curator` | `curator123` | Curator |
| `analyst` | `analyst123` | Analyst |
| `user` | `user123` | User |

## 7) Jak to funguje

### Ingest

1. validace URL a role
2. pokus o HTML fetch
3. když je text slabý, použije se Playwright render
4. když je potřeba, doplní se text z full-page screenshotu přes OCR
5. volitelně se nad screenshotem spustí vision extrakce do sekcí a tabulek
6. uloží se evidence
7. pokud je detekovaná CAPTCHA / bot challenge, uloží se incident a stránka se neindexuje
8. jinak se vytvoří canonical document
9. textové sekce a případné tabulky se rozdělí na chunky
10. chunky se naembedují a uloží do Qdrantu
11. při re-ingestu stejné URL se stará verze smaže

### Query

- `mode=rag`: query embedding -> Qdrant search -> score filter -> LLM odpověď s citacemi
- když jsou v retrievalu dostupné screenshoty a je zapnutý vision mód, pošlou se spolu s textovým kontextem do multimodálního modelu
- `mode=no-rag`: přímý dotaz na LLM bez retrieval

`mode` je validovaný enum, takže jsou povoleny jen hodnoty `rag` a `no-rag`.

## 8) Důležité endpointy a role

- `POST /api/auth/login` -> login
- `GET /api/ingest/sources` -> všechny role
- `POST /api/ingest/sources` -> `Admin`, `Curator`
- `POST /api/ingest/run` -> `Admin`, `Curator`
- `POST /api/query/` -> všechny role

`POST /api/ingest/run` navíc validuje, že cílová URL zůstává v scope zvoleného `source.base_url`.
Při detekci CAPTCHA vrátí ingest `status=blocked_captcha`, uloží evidence + incident, ale nevytvoří indexovaný dokument.

## 9) Důležitá konfigurace

| Variable | Default | Meaning |
|---|---|---|
| `APP_SECRET_KEY` | `change-me` | JWT secret, změň |
| `OLLAMA_MODEL` | `llama3.2:3b` | textový model pro generování odpovědí |
| `OLLAMA_VISION_MODEL` | prázdné | multimodální model pro screenshoty, typicky Qwen |
| `VISION_ANSWER_ENABLED` | `false` | při `rag` pošle relevantní screenshoty i do LLM |
| `VISION_EXTRACT_ON_INGEST` | `false` | při screenshot fallbacku zkusí structured vision extrakci |
| `VISION_MAX_IMAGES` | `2` | kolik screenshotů max posílat do answer fáze |
| `RETRIEVAL_MIN_SCORE` | `0.25` | minimální relevance retrieval hitu |
| `QUALITY_THRESHOLD_CHARS` | `300` | hranice pro přepnutí na render fallback |
| `FETCH_VERIFY_SSL` | `true` | ověření TLS certifikátů při HTML fetchi; pro lokální problematické CA lze v dev prostředí dočasně vypnout |

## 10) Testy

Projekt obsahuje smoke testy pro:
- HTML ingest
- RENDERED_DOM ingest
- SCREENSHOT fallback
- structured vision ingest nad screenshotem
- vision failure fallback zpět na OCR/text
- invalid `mode`
- `no-rag` query
- multimodální `rag` answer se screenshotem
- retrieval threshold
- `rag` bez výsledků
- blokace ingestu mimo scope vybraného source
- CAPTCHA stránka se neindexuje a vyčistí starou verzi dokumentu

Spuštění:

```powershell
pytest
```

## 11) Bezpečnost a limity

### Bezpečnost

- blokované jsou neveřejné / lokální IP adresy i po DNS resolve
- kontrolují se i redirecty při fetchi
- login rate limit je 5 pokusů za 60 sekund na IP
- audit log ukládá důležité akce

### Aktuální limity MVP

- ingest je synchronní
- retrieval je čistě vektorový, bez BM25
- multimodální answer a screenshot ingest už umí jednoduchou vision vrstvu, ale ne detailní layout parsing s bounding boxy
- bez běžící Ollamy nejsou LLM odpovědi dostupné
- bez migrací schématu je změna DB řešená znovu přes `init_db`
- permission metadata zatím nejsou promítnuté do retrieval filtru

### Plánované rozšíření

Záměrně odložená je nejtěžší část:
- bounding boxy a přesná citace na oblast screenshotu
- robustní layout detekce bloků stránky
- silnější extrakce tabulek do přesnější struktury

Aktuální verze proto řeší nejdřív praktické minimum: multimodální answer nad relevantním screenshotem a volitelnou structured vision extrakci při ingestu.

## 12) Výběr modelu pro lokální testování a větší GPU

Doporučení k rodině Qwen3.5 je v souboru:
- `VYBER_MODELU_QWEN35.md`
