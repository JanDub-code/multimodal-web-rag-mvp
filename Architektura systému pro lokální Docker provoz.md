# Architektura systému pro lokální Docker provoz

Datum: 2026-04-02  
Status: závazný dokument pro aktuální MVP

## 1. Cíl dokumentu

Tento dokument je hlavní zdroj pravdy pro:
- aktuální runtime architekturu (`AS-IS`),
- cílový růstový model (`TO-BE`),
- pravidla struktury repozitáře (dříve samostatně v `Monorepo standard.md`),
- pořadí implementačních kroků.

Pracovní princip:
- nejdřív spolehlivý local Docker run,
- potom provozní minimum,
- až nakonec růstové vrstvy (workers/redis/contract refaktor).

## 2. Aktuální stav (AS-IS)

## 2.1 Runtime profily

### Profil `core` (default)

Služby:
- `api`
- `postgres`
- `qdrant`

Charakteristika:
- plně použitelný ingest + query runtime,
- Ollama může běžet mimo compose (host/external),
- vhodný pro vývoj a běžné lokální testování.

### Profil `core + ollama` (volitelný)

Služby:
- `api`
- `postgres`
- `qdrant`
- `ollama`

Charakteristika:
- plný lokální stack v Dockeru,
- vhodný pro „vše v jednom“ běh.

## 2.2 One-command orchestrace

Oficiální vstup:
- `./scripts/dev-up.sh`
- `./scripts/dev-up.sh --with-ollama`

Script dělá:
1. start infrastruktury,
2. `alembic upgrade head`,
3. seed default uživatelů,
4. start API.

## 2.3 Provozní minimum

- `GET /health`:
  - required: `postgres`, `qdrant`,
  - optional: `ollama`.
- `X-Request-ID`:
  - převzetí z requestu nebo generace,
  - echo v response,
  - propis do auditu.
- Auth:
  - login (`access_token` + `refresh_token`),
  - refresh rotace tokenu,
  - logout revoke refresh tokenu.
- DB schema:
  - pouze přes Alembic migrace,
  - `init_db` je seed-only.

## 2.4 Stav implementace (souhrn)

| Oblast | Stav |
|---|---|
| Docker API service + compose core profil | SPLNĚNO |
| Volitelný `ollama` profil | SPLNĚNO |
| One-command startup script | SPLNĚNO |
| Health endpoint | SPLNĚNO |
| Request ID + audit propagation | SPLNĚNO |
| Alembic migrace + seed-only init | SPLNĚNO |
| Refresh token flow (DB-backed) | SPLNĚNO |
| Reálný end-to-end smoke na čistém stroji | K DOOVĚŘENÍ |
| Test execution report v aktuálním prostředí | K DOOVĚŘENÍ |

## 3. Standard repozitáře (sjednocený monorepo režim)

## 3.1 MVP baseline (závazné nyní)

Povolená top-level struktura:

```text
/
├── app/
├── data/
├── scripts/
├── tests/
├── alembic/
├── docker-compose.yml
├── Dockerfile
├── alembic.ini
├── requirements.txt
├── README.md
└── .env.example
```

Pravidla:
- core business logika je v `app/`,
- schema změny jen přes Alembic,
- `scripts/` neobsahují business pravidla,
- runtime musí zůstat spustitelný přes local Docker profil `core`,
- žádný velký strukturální refaktor bez růstových triggerů.

## 3.2 Scale target (cílový stav při růstu)

Cílová struktura při škálování:

```text
/
├── apps/
├── workers/
├── packages/
├── infra/
├── docs/
├── tests/
└── scripts/
```

Motivace:
- separace běhových částí,
- nezávislé release cykly,
- sdílené kontrakty v `packages`,
- jasnější ownership napříč týmy.

## 3.3 Migration triggers (kdy přejít na Scale target)

Přechod se spouští až při splnění alespoň jednoho bodu:
- potřeba async throughputu (fronty/workeři),
- oddělené release cykly API vs worker,
- více ownerů/týmů nad nezávislými částmi systému,
- tlak na stabilní servisní kontrakty.

Bez triggeru je závazný režim `MVP baseline`.

## 4. Roadmapa (jak budeme postupovat)

## Fáze P0 - dotažení provozní použitelnosti

1. Ověřit `dev-up` skripty na čistém prostředí.
2. Zapsat krátký troubleshooting runbook.
3. Potvrdit idempotenci migrací + seedu.

Výstup:
- spolehlivý „one-command local docker run“ bez ručního dohledávání.

## Fáze P1 - provozní disciplína

1. Stabilní test run + report.
2. CI minimum (tests + migrace smoke).
3. Údržba expirovaných refresh tokenů.
4. Udržení dokumentace v souladu s runtime.

Výstup:
- opakovatelný a kontrolovatelný provozní baseline.

## Fáze P2 - růstové vrstvy (až dle triggerů)

1. Consent enforcement model.
2. Async orchestrace (`redis` + workers).
3. Inference contract modul.
4. ADR rozhodnutí `Qdrant vs pgvector`.
5. Rozšířená observability + backup runbook.

Výstup:
- škálovatelný model bez předčasné režie.

## 5. Co teď vědomě neděláme

- refaktor do `apps/workers/packages/...` jen kvůli „čistotě“,
- zavedení redis/worker vrstvy bez reálného throughput tlaku,
- přepis retrieval vrstvy jen kvůli formální shodě s jiným dokumentem,
- plná observability platforma před stabilizací lokálního runtime.

## 6. Akceptační kritéria pro aktuální etapu

Systém je v „ready baseline“ stavu, pokud:
- `dev-up` startuje stack bez ručního zásahu,
- `GET /health` korektně reportuje required/optional komponenty,
- ingest/query flow funguje v Docker runtime,
- auth login/refresh/logout flow je funkční,
- migrace jsou jediný mechanismus schema změn,
- request ID je dohledatelné v API response i auditu,
- dokumentace odpovídá reálnému chování repozitáře.

