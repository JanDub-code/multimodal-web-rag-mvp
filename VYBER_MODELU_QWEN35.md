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

## Dopad na tuto aplikaci

V kontextu tohoto MVP:
- ingest a retrieval pipeline se nemění,
- mění se pouze backend/model a kvalita odpovědí,
- není nutné přepisovat architekturu aplikace.

## Stručné doporučení

- **do 12 GB VRAM:** Qwen3.5-4B
- **16–24 GB VRAM:** Qwen3.5-9B
- **24+ GB VRAM:** Qwen3.5-27B

Nejpraktičtější lokální postup:

**4B/9B pro vývoj -> 27B jen pokud má lokální hardware rezervu**

