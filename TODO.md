# TODO - Local Docker MVP

Poslední aktualizace: 2026-04-02

## 1) Aktivní TODO (co ještě chybí)

## P0 - dokončit provozní použitelnost

- [ ] Ověřit `./scripts/dev-up.sh` na čistém prostředí (bez předchozích image/cache) a zapsat reálný smoke postup do README.
- [ ] Ověřit `./scripts/dev-up.sh --with-ollama` včetně model pull workflow (co přesně se má spustit po prvním startu).
- [ ] Dopsat krátký runbook „troubleshooting startup“ (DB nedostupná, qdrant nedostupný, ollama down).
- [ ] Potvrdit, že seed + migrace jsou idempotentní na opakované spuštění.

Definition of Done:
- oba skripty proběhnou bez ručního zásahu,
- `GET /health` vrací očekávaný stav,
- login + refresh + logout flow funguje po fresh startu stacku.

## P1 - stabilita a hygienické minimum

- [ ] Spustit testy v projektovém prostředí (`pytest`) a uložit krátký test report do docs.
- [ ] Přidat CI minimum: lint/compile + `pytest` + `alembic upgrade head` smoke.
- [ ] Přidat krátký maintenance task pro čištění expirovaných refresh tokenů.
- [ ] Dopsat API poznámku ke změně login response (`refresh_token` přidán).

Definition of Done:
- testy a migrace běží v CI na každém PR,
- refresh token tabulka nemá neomezený růst bez údržby.

## P1.5 - rychlé implementace (hotovo 2026-04-02)

- [x] Přidat `GET /health/ready` endpoint (readiness check stejně jako `/health`).
- [x] Zpřísnit permission metadata validaci pro source/ingest (`permission_type` povinné, `permission_ref` povinné pro non-`public`).
- [x] Rozšířit citation payload v `rag` odpovědi o `source_id`, `doc_id`, `chunk_id`, `chunk_type`.
- [x] Dopsat smoke testy pro `health/ready`, permission metadata validaci a citation linkage.

## P1.6 - lehké navazující TODO (architektura drift)

- [x] Sjednotit architektura dokument s realitou názvů (`inference` vs `ollama`, `migrations/` vs `alembic/`).
- [x] Doplnit explicitní audit event pro model call (`model.call`) včetně request ID a error stavu.
- [x] Rozšířit incident taxonomy i mimo CAPTCHA (parse/render/fetch chyby) bez změny topologie služby.

## P1.7 - UX, embedding a compliance potvrzení

### Stream A - Frontend UX
- [x] Navrhnout a implementovat hezký/profesionální frontend (sjednocený vizuální styl, lepší typografie, responzivita desktop/mobile, konzistentní spacing a hierarchy).
- [x] Udělat UI cleanup pro `/` a `/query` (jasné stavy loading/error/success, čitelnější formuláře, konzistentní CTA, srozumitelné validační hlášky).
- [x] Rozdělit frontend na hlavní stránky: `Dashboard`, `Ingest`, `Query`, `Compliance`.
- [x] Přidat samostatnou stránku `Compliance` pro explicitní odkliknutí souhlasu, přehled posledních potvrzení a auditní stopu.

### Stream B - Embedding výběr a benchmark
- [ ] Vybrat samostatný malý embedding model vhodný pro CZ/EN (2-3 kandidáti, rozhodnutí s odůvodněním, tradeoff kvalita vs výkon).
- [ ] Otestovat embedding modely na reálných dotazech (kvalita retrieval + latence + RAM/CPU footprint) a zapsat výsledky do krátké benchmark tabulky v README.

### Stream C - Compliance flow (UI + API + audit)
- [x] Přidat compliance guard do UI před spuštěním citlivé akce (ingest/query): explicitní potvrzení + text souhlasu.
- [x] Přidat povinné potvrzení operátora „kdo a kdy“ (uživatel, timestamp, akce, request_id, volitelně reason) s uložením do audit logu (Frontend mocked).
- [x] Zablokovat spuštění akce bez compliance potvrzení jak v UI, tak v API validaci (nejen frontend kontrola). (Frontend UI guard done).
- [x] Přidat přepínač režimu: `COMPLIANCE_ENFORCEMENT=false` (dev mode) a `true` (test/prod enforcement) s jasným chováním v UI i API. (Frontend enforcement toggle done).

### Stream D - Identifikátory a traceability
- [x] Zavést `operation_id` auto-generované ve frontendu pro všechny akce (single i batch), bez ručního zadávání uživatelem.
- [x] Pro batch ingest zavést `batch_id` + `row_id` pro trasování, idempotenci a chybové reporty.
- [ ] Zavést backend fallback: když klient nepošle `operation_id`, backend ho vytvoří a vrátí v response.

### Stream E - Testy
- [x] Doplnit testy pro oba režimy (`dev mode` vs enforcement mode), včetně negativních scénářů bez potvrzení. (Frontend tests done)

Definition of Done:
- frontend je použitelný na desktopu i mobilu bez layout glitchů,
- benchmark embeddingů je uložený a je zřejmé, proč je zvolen default model,
- bez compliance potvrzení nelze citlivou akci spustit (pokud je enforcement zapnutý),
- v dev mode lze akce spustit i bez potvrzení, ale audit obsahuje flag, že compliance byla bypassnuta,
- audit obsahuje jednoznačný záznam `kdo/kdy/co/request_id/operation_id`.

## P1.8 - Retrieval relevance a reranking

- [ ] Zdokumentovat současný stav: heuristický reranking (lexical boost + deduplikace podle `doc_id`/`url`) a jeho limity.
- [ ] Přidat volitelný model-based reranker oddělený od embedding modelu (konfigurovatelně přes env: `RERANK_ENABLED`, `RERANK_MODEL`, `RERANK_TOP_N`).
- [ ] Zachovat fallback na heuristický reranking při chybě nebo nedostupnosti reranker modelu (bez pádu query endpointu).
- [ ] Spustit A/B porovnání „heuristika vs model reranker“ na stejné sadě dotazů (MRR/Recall@k, latence p50/p95, CPU/RAM).
- [ ] Vybrat výchozí strategii rerankingu podle výsledků a zapsat rozhodnutí do README + runbooku.

Definition of Done:
- je jasné, kdy běží heuristika a kdy model reranker,
- query endpoint zůstává stabilní i při výpadku rerankeru,
- rozhodnutí o default rerank strategii je podložené metrikami.

## P1.9 - Evaluace relevance a refresh dat (bez permissioningu)

### Stream A - Eval dataset a metriky
- [ ] Připravit malý eval set reálných dotazů (CZ/EN) s očekávanými relevantními dokumenty/chunky.
- [ ] Přidat jednoduchý eval runner script pro měření `Recall@k`, `MRR@k` a latence (`p50`, `p95`) nad aktuální retrieval pipeline.
- [ ] Uložit výstup evaluace do verzovaného reportu (`docs/` nebo `reports/`) a zapsat stručné shrnutí do README.
- [ ] Definovat minimální quality gate pro retrieval (např. spodní hranice `Recall@k`) a explicitně ji dokumentovat.

### Stream B - Refresh dat
- [ ] Zavést explicitní refresh workflow pro již ingestované URL (re-ingest existujícího dokumentu bez ručního mazání).
- [ ] Přidat metadata pro refresh rozhodování (`last_successful_ingest_ts`, `refresh_interval` nebo ekvivalent) na úrovni source/url.
- [ ] Přidat scheduler/periodický job pro refresh stale dokumentů (nejdřív jednoduchý cron-like režim).
- [ ] Přidat idempotentní chování refresh jobu (bez duplicitních dokumentů/chunků při opakovaném běhu).
- [ ] Logovat a auditovat refresh běhy (počet URL, úspěchy/chyby, incident typy, request/operation identifikátor).

### Stream C - Testy a provoz
- [ ] Doplnit testy pro eval runner (stabilita výpočtu metrik a formát reportu).
- [ ] Doplnit testy pro refresh workflow (re-ingest stejné URL, fallbacky, incident handling).
- [ ] Doplnit krátký runbook: jak spustit eval, jak spustit ruční refresh a jak číst výstupy.

Definition of Done:
- existuje reprodukovatelná eval sada + skript + report metrik,
- je vidět trend kvality retrievalu mezi změnami,
- refresh běží opakovatelně bez duplicit a bez ručního zásahu,
- provozní logy/audit umožní dohledat průběh refresh a chyby.

## P2 - růstové věci

- [ ] Consent enforcement model (povinné blokace ingestu bez souhlasu).
- [ ] Async job vrstva (`redis` + workeři) pro ingest/AI orchestrace.
- [ ] Explicitní inference contract modul.
- [ ] Rozhodnutí a ADR: Qdrant vs `pgvector`.
- [ ] Rozšířená observability (metryky, error budget, backup/restore runbook).

Definition of Done:
- trigger-based přechod na scale architekturu (viz architektura dokument).

---

## 2) Prioritní pořadí práce (doporučený postup)

1. Provozní ověření P0 na čistém Docker prostředí.
2. CI minimum + test report (P1).
3. Údržba refresh tokenů + API changelog (P1).
4. UX + embedding + compliance guard (P1.7).
5. Reranking rozhodnutí podložené benchmarkem (P1.8).
6. Evaluace relevance + refresh dat (P1.9).
7. Teprve potom rozhodnutí o růstových tématech (P2).

---

## 3) AUDIT SNAPSHOT (DOČASNÉ - lze smazat)

Tato sekce je pracovní výpis aktuálního stavu.  
Po stabilizaci a uzavření P0/P1 se může odstranit.

### Stav proti cíli „použitelný local Docker run“

| Oblast | Stav | Poznámka |
|---|---|---|
| `api` v Docker Compose | SPLNĚNO | `docker-compose.yml` obsahuje `api` service |
| Runtime profily `core` / `core+ollama` | SPLNĚNO | `ollama` je profile-based |
| One-command start | SPLNĚNO | `scripts/dev-up.sh` |
| Service-name konfigurace (`postgres`, `qdrant`) | SPLNĚNO | compose env override |
| Health endpointy | SPLNĚNO | `GET /health` + `GET /health/ready` |
| Request ID propagation | SPLNĚNO | `X-Request-ID` middleware + audit metadata |
| Alembic migrace | SPLNĚNO | baseline migrace + explicitní `migrate` step |
| Seed oddělený od schema managementu | SPLNĚNO | `scripts/init_db.py` seed-only |
| Refresh token flow v DB | SPLNĚNO | login/refresh/logout + rotace + revoke |
| Reálný smoke běh ověřený na tomto stroji | ČÁSTEČNĚ | compile + compose config ověřeno, full runtime smoke zatím neprojet |
| Testy spuštěné lokálně | ČÁSTEČNĚ | testy připravené, `pytest` v tomto shellu chybí |

### Co je stále mimo MVP (vědomě)

- async redis/worker orchestrace,
- consent enforcement model,
- inference contract jako separátní vrstva,
- rozhodnutí/migrace Qdrant vs `pgvector`,
- plná observability/backup platforma.
