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
4. Teprve potom rozhodnutí o růstových tématech (P2).

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
| Health endpoint | SPLNĚNO | `GET /health` required/optional komponenty |
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

