# Architektura systému

## 1. Účel dokumentu

Tento dokument definuje závaznou architekturu systému pro:

- sběr a zpracování webového obsahu,
- ukládání důkazních artefaktů,
- auditovatelnou AI analýzu,
- odpovědi s citacemi,
- lokální provoz přes Docker Compose.

Dokument sjednocuje architekturu aplikace, provozní minimum a minimální standard struktury repozitáře.

---

## 2. Cíle systému

Systém musí splnit tyto cíle:

- být spustitelný jedním příkazem v lokálním Docker prostředí,
- držet hlavní produktový tok v jedné srozumitelné aplikaci,
- ukládat artefakty a auditní stopu tak, aby šlo dohledat původ odpovědí,
- podporovat režimy `rag` i `no-rag`,
- být rozšiřitelný bez nutnosti předčasného štěpení do mnoha služeb.

---

## 3. Zásady návrhu

### 3.1 Jednoduchost je výchozí stav

Používají se jen komponenty, které mají přímý provozní přínos.

Nová vrstva se přidává jen tehdy, když:

- řeší reálný problém výkonu nebo spolehlivosti,
- snižuje složitost místo jejího přesunu jinam,
- odděluje část systému, která už má jiný životní cyklus než zbytek aplikace.

### 3.2 Jedna provozní topologie

Vývojové a lokální provozní prostředí používá stejný Docker Compose stack.

Rozdíly mezi prostředími se řeší jen přes:

- `.env` konfiguraci,
- limity,
- velikost dat,
- parametry modelu,
- počet instancí, pokud to bude později potřeba.

### 3.3 Jedna hlavní aplikace

Základní architektura je postavená kolem jedné FastAPI aplikace, která nese:

- HTTP API,
- auth,
- orchestraci ingestu,
- query vrstvu,
- auditní zápisy,
- incident handling,
- administrační nebo interní UI, pokud je součástí stejného runtime.

### 3.4 Dohledatelnost je povinná

Každý významný krok musí být zpětně dohledatelný minimálně přes:

- uživatele,
- zdroj,
- dokument,
- artefakty,
- citace,
- request ID,
- auditní události.

---

## 4. Provozní model

## 4.1 Základní runtime

Systém běží jako lokální Docker Compose stack.

Povinné běhové části:

- `api` — hlavní FastAPI aplikace,
- `postgres` — relační databáze pro metadata, audit a aplikační stav,
- `qdrant` — vektorové vyhledávání,
- evidence storage — lokální bind mount nebo volume pro důkazní artefakty a pracovní soubory.

Volitelné běhové části:

- `ollama` inference backend jako samostatná Compose služba (profil `ollama`) nebo externí host backend,
- `migrate` jednorázová service pro `alembic upgrade head` (profil `tools`),
- `playwright` helper nebo Playwright runtime uvnitř `api`,
- reverzní proxy,
- zálohovací job,
- oddělený frontend, pokud přestane stačit UI uvnitř hlavní aplikace.

## 4.2 Konfigurační pravidla

Veškerá service-to-service komunikace v Dockeru používá názvy služeb, ne `localhost`.

Příklady:

- databáze: `postgres`
- vektorová vrstva: `qdrant`
- inference backend: `ollama` (nebo externí host přes `DOCKER_OLLAMA_URL`)

Aplikace nesmí být vázaná na lokální host-only konfiguraci, která by rozbíjela kontejnerový běh.

---

## 5. Hranice systému

## 5.1 API a aplikační vrstva

FastAPI aplikace je hlavní řídicí vrstva systému.

Odpovídá za:

- autentizaci a autorizaci,
- validaci vstupů,
- správu zdrojů,
- spuštění ingest workflow,
- volání retrieval vrstvy,
- volání inference backendu,
- sestavení odpovědi s citacemi,
- zápis auditu,
- zakládání a správu incidentů,
- health endpointy a základní provozní diagnostiku.

## 5.2 Relační data

PostgreSQL je jediný zdroj pravdy pro:

- uživatele,
- role metadata v tabulce uživatelů,
- refresh token metadata,
- zdroje,
- permission metadata,
- ingest joby,
- dokumenty,
- chunky,
- embedding metadata,
- incidenty,
- auditní log,
- metadata důkazních artefaktů.

Citace jsou ukládány v `chunks.citations_ref` a v payloadu Qdrant bodů.

Schéma databáze se mění výhradně přes Alembic migrace (`alembic/versions`).

Ruční `init_db` přístup není dostatečný jako dlouhodobý standard.

## 5.3 Vektorové vyhledávání

Qdrant slouží pro embeddingy a retrieval nad chunky.

Použití:

- ukládání embeddingů,
- similarity search,
- kandidáty pro RAG odpovědi,
- omezení počtu vstupních pasáží pro model.

Relační metadata a vazby zůstávají v PostgreSQL. Vektorová vrstva není zdroj pravdy pro doménová data.

## 5.4 Evidence a artefakty

Binární a důkazní artefakty se ukládají do lokální storage (volume nebo bind mount).

Typy artefaktů:

- screenshoty,
- HTML snapshoty,
- DOM exporty,
- OCR nebo vision výstupy,
- PDF důkazy,
- canonical JSON exporty,
- pomocné pracovní soubory.

Databáze ukládá:

- cestu nebo URI,
- hash,
- typ artefaktu.

Vazby na zdroj, dokument a chunk jsou v aktuální verzi dohledatelné přes citation metadata (`evidence_ids`/`evidence_items`) a workflow záznamy.

## 5.5 Inference hranice

Aplikace nesmí mít modelové volání rozházené po náhodných modulech.

Volání modelu se soustřeďuje do jedné integrační vrstvy, která sjednocuje:

- request payload,
- response payload,
- timeout,
- retry,
- chybový model,
- audit metadata,
- request ID.

Závazná cesta:

`API -> service layer -> multimodal client -> inference backend`

Používá se jeden hlavní inference backend (aktuálně Ollama kompatibilní HTTP API).

---

## 6. Auth a autorizace

## 6.1 Auth model

Autentizace je součástí FastAPI aplikace.

Použitý model:

- `fastapi.security.OAuth2PasswordBearer`,
- JWT access token,
- refresh token,
- hashování hesel,
- role-based access control v aplikační vrstvě.

## 6.2 Povinné auth chování

Systém musí podporovat:

- login,
- vydání access tokenu,
- vydání refresh tokenu,
- obnovu access tokenu,
- logout nebo invalidaci refresh tokenu,
- role guard na chráněných endpointůch,
- audit login a security událostí.

## 6.3 Role model

Minimální role model:

- `admin` — správa systému a uživatelů,
- `curator` — správa zdrojů, ingest a incidenty,
- `analyst` — dotazování, analýza a práce s výsledky,
- případně `user`, pokud systém zpřístupňuje omezenou samoobsluhu.

---

## 7. Ingest a zpracování zdrojů

## 7.1 Základní ingest pipeline

Systém používá řízený fallback pro sběr obsahu.

Preferované pořadí:

1. HTML fetch,
2. rendered DOM,
3. screenshot,
4. OCR nebo vision doplnění, pokud je potřeba.

Pipeline musí umět:

- uložit raw podklady,
- vytvořit evidence artefakty,
- založit dokument,
- vytvořit chunky,
- vytvořit embeddingy,
- připravit data pro citace a retrieval.

## 7.2 Incident stop

Workflow musí umět sběr zastavit a založit incident minimálně při:

- CAPTCHA nebo blokaci přístupu,
- nedostupnosti zdroje,
- nevalidním výsledku renderu,
- chybě parsování,
- porušení lokálních validačních pravidel.

Incident musí být dohledatelný a navázaný na zdroj i artefakty, které při pokusu vznikly.

## 7.3 Permission a oprávnění ke zdroji

Každý zdroj musí mít uložené permission metadata.

Ingest nesmí být spuštěn nad zdrojem bez vyplněných minimálních informací o oprávnění nebo interním důvodu zpracování.

Minimální evidované položky:

- typ oprávnění,
- reference nebo poznámka k oprávnění,
- uživatel, který zdroj založil nebo schválil,
- čas vytvoření nebo změny.

---

## 8. Query a odpovědi

## 8.1 Režimy odpovědi

Systém podporuje dva režimy:

- `rag` — odpověď vzniká nad retrieved pasážemi,
- `no-rag` — odpověď vzniká bez retrieval kontextu.

## 8.2 Povinné chování query vrstvy

Query vrstva musí umět:

- vyhledat relevantní chunky,
- vrátit citace použitých pasáží,
- uložit auditní záznam dotazu,
- navázat odpověď na konkrétní retrieval výsledek,
- odlišit odpovědi s retrieval kontextem a bez něj.

## 8.3 Citace

Každá odpověď v `rag` režimu musí nést citace navázané na konkrétní chunky a dokumenty.

Citace musí být zpětně dohledatelné na:

- dokument,
- chunk,
- zdroj,
- případně důkazní artefakt, pokud je součástí odpovědi.

---

## 9. Audit, logování a observability minimum

## 9.1 Audit

Auditní vrstva zapisuje minimálně:

- login a logout události,
- založení nebo změnu zdroje,
- spuštění ingestu,
- vznik incidentu,
- query request,
- modelové volání.

## 9.2 Correlation a request ID

Každý request a každý navazující interní krok musí nést request ID nebo correlation ID.

Toto ID musí být přítomné minimálně v:

- HTTP logu,
- auditním záznamu,
- chybovém logu,
- modelovém volání,
- incidentu, pokud vznikne z konkrétního requestu.

## 9.3 Health endpointy

Systém musí mít minimálně:

- `GET /health` — proces žije,
- `GET /health/ready` — aplikace umí obsloužit provoz,
- volitelně detailnější interní diagnostiku pro DB, Qdrant a inference backend.

## 9.4 Metriky

Plnohodnotná observability platforma není součást základní architektury.

Závazné minimum je:

- konzistentní strukturované logování,
- request ID,
- health endpointy,
- jasný chybový model.

---

## 10. Docker provozní standard

## 10.1 Povinné soubory

Repozitář musí obsahovat minimálně:

- `Dockerfile`
- `docker-compose.yml`
- `.env.example`
- `README.md`
- migrace databáze

## 10.2 Povinné vlastnosti compose stacku

Compose stack musí:

- spustit aplikaci bez ručního lokálního nastavování host-dependent adres,
- připojit persistentní storage pro databázi a evidence (volume nebo bind mount),
- používat service names pro vnitřní komunikaci,
- umožnit jednoduchý `up` a `down` cyklus,
- mít oddělenou konfiguraci pro tajemství a běžné parametry.

## 10.3 Backupy

Minimální doporučený standard:

- pravidelný dump PostgreSQL,
- snapshot nebo archivace evidence volume,
- zdokumentovaný restore postup.

---

## 11. Standard struktury repozitáře

Závazná baseline struktura repozitáře je malá a odpovídá současnému rozsahu projektu.

```text
/
├── app/
├── data/
├── scripts/
├── tests/
├── alembic/
├── docker-compose.yml
├── Dockerfile
├── README.md
├── .env.example
└── pyproject.toml nebo requirements.txt
```

## 11.1 Význam adresářů

### `app/`

Obsahuje hlavní FastAPI aplikaci a veškerou aplikační logiku.

Uvnitř mají být logicky oddělené minimálně tyto části:

- API routes,
- auth,
- services,
- models,
- schemas,
- repositories nebo DB access,
- config,
- main entrypoint.

### `data/`

Obsahuje runtime data mimo databázi:

- evidence,
- exporty,
- pomocné soubory,
- případně lokální cache, pokud je opravdu potřeba.

### `scripts/`

Obsahuje jen podpůrné skripty.

Do `scripts/` nepatří core business logika, kterou potřebuje běžící aplikace.

### `tests/`

Obsahuje unit, integration a případně e2e testy.

### `alembic/`

Obsahuje výhradně databázové migrace.

---

## 12. Pravidla pro růst architektury

Architektura zůstává v této jednoduché podobě, dokud platí alespoň většina z následujících bodů:

- jedna aplikace je pořád čitelná a udržitelná,
- ingest nevyžaduje oddělený asynchronní throughput,
- release cyklus API a zpracování je společný,
- tým nepotřebuje samostatně spravované služby,
- docker provoz zůstává jednoduchý a stabilní.

Teprve při splnění růstových triggerů má smysl zavést:

- samostatné workery,
- fronty,
- oddělené packages vrstvy,
- více runtime služeb,
- rozsáhlejší observability stack.

Samotná možnost takové změny není důvod ji dělat předčasně.

---

## 13. Minimální akceptační kritéria

Architektura je považována za naplněnou, pokud systém umí:

1. spustit se přes Docker Compose,
2. přihlásit uživatele a vynutit role,
3. založit zdroj,
4. uložit permission metadata ke zdroji,
5. spustit ingest,
6. vytvořit evidence artefakty,
7. uložit dokument a chunky,
8. vyhledat relevantní pasáže,
9. vrátit odpověď s citacemi v `rag` režimu,
10. vrátit odpověď v `no-rag` režimu,
11. zapsat auditní stopu,
12. vrátit stav přes health endpoint.

---

## 14. Rozhodovací pravidlo

Výchozí pravidlo pro další změny je jednoduché:

- nejdřív udržet spolehlivý one-command Docker provoz,
- potom zlepšovat kvalitu a dohledatelnost,
- teprve nakonec přidávat nové architektonické vrstvy.

Architektura systému má zůstat malá, srozumitelná a provozně levná, dokud si růst složitější model reálně nevynutí.
