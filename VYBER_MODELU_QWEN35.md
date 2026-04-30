# Výběr modelu pro lokální testování (Qwen3.5)

## Doporučení pro tento workflow

Pro tento projekt je **Qwen3.5** vhodná multimodální rodina modelů, protože umožňuje škálovat kvalitu bez změny architektury aplikace.

V praxi:
- menší model pro rychlý lokální vývoj,
- větší model pro kvalitnější odpovědi na výkonnějším lokálním stroji.

## Praktický výběr podle VRAM

### 8–12 GB VRAM

- doporučení: **Qwen3.5-4B**
- fallback pro velmi slabé GPU: **2B** nebo **0.8B**

### 16–24 GB VRAM

- doporučení: **Qwen3.5-9B**
- dobrý kompromis kvalita/výkon pro běžný lokální provoz

### 24+ GB VRAM

- doporučení: **Qwen3.5-27B**
- vhodné, pokud je prioritou kvalita a stroj má dost paměti

## Poznámka k variantě 35B-A3B

**35B-A3B** není vhodné chápat jako levný 3B model.

I když je během inference aktivní menší část parametrů než u dense modelu stejné velikosti, provozně je to stále velký model se značnými nároky na paměť a infrastrukturu.

## Hodnocení Tiny modelů (≤4B parametrů)

Pro lokální běh MVP na běžném hardwaru jsme zhodnotili dvě nejlepší varianty v kategorii malých modelů. Primárním základem, který chceme pro toto MVP rovnou otestovat, bude Qwen3.5 2B.

1. **Qwen3.5 2B (Reasoning)**
   - **Velikost:** 2.27 miliardy aktivních parametrů
   - **Context Window:** 262k tokenů
   - **Hodnocení:** Náš výchozí cíl k vyzkoušení. Přestože je výrazně menší, dosahuje maximálních výsledků v "tiny" kategorii, je extrémně lehký na RAM/VRAM a zachovává bezkonkurenční velikost kontextu pro naši RAG pipeline.

2. **Nanbeige4.1-3B**
   - **Velikost:** 3.93 miliardy parametrů
   - **Context Window:** 256k tokenů
   - **Hodnocení:** Silný vyzyvatel se stejným hodnocením inteligence (16 bodů). Avšak s téměř dvojnásobkem parametrů proti Qwen3.5 2B vyžaduje silnější hardware, a proto figuruje spíše jako záloha/porovnávací model.

## Dopad na tuto aplikaci

V kontextu tohoto MVP:
- ingest a retrieval pipeline se nemění,
- mění se pouze backend/model a kvalita odpovědí,
- architektura aplikace zůstává stejná.

## Stručné doporučení

- **do 12 GB VRAM:** Qwen3.5-4B
- **16–24 GB VRAM:** Qwen3.5-9B
- **24+ GB VRAM:** Qwen3.5-27B

Nejpraktičtější lokální postup:

**4B/9B pro vývoj -> 27B jen pokud má lokální hardware rezervu**
