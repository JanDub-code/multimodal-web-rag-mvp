# Výběr modelu pro lokální testování a nasazení na školním GPU / Metacentru

## Doporučení pro tento workflow

Pro tento workflow je **Qwen3.5** rozumná volba jako jedna škálovatelná multimodální rodina modelů. Praktická výhoda je, že lze doma testovat menší variantu a na školním GPU serveru nebo v Metacentru nasadit větší variantu bez změny celé architektury aplikace nebo základního promptovacího stylu.

To se hodí hlavně pro tento projekt, protože aplikace odděluje:
- ingest,
- retrieval,
- answer generation,
- a backend modelu lze měnit bez zásahu do zbytku pipeline.

## Praktický výběr podle dostupné VRAM

### 8–12 GB VRAM doma
Začni na **Qwen3.5-4B**.

Je to rozumný kompromis mezi kvalitou a nároky na hardware. Pokud je GPU slabší nebo je cílem jen rychle ověřit pipeline, lze použít i **2B** variantu. **0.8B** dává smysl hlavně pro úplné prototypování a kontrolu, že vše technicky běží.

### 16–24 GB VRAM doma
Jako nejlepší výchozí volba dává smysl **Qwen3.5-9B**.

Je už dost velký na to, aby mělo smysl hodnotit multimodální chování, ale stále realistický pro lokální inference a vývoj.

### Větší školní GPU server / Metacentrum
Pro první serióznější multimodální deployment dává smysl **Qwen3.5-27B**.

Je to stále dense model a z provozního hlediska bývá jednodušší než MoE varianta **35B-A3B**.

## Poznámka k variantě 35B-A3B

**35B-A3B** není vhodné chápat jako „levný 3B model“.

I když má nižší počet aktivovaných parametrů během inference než plně dense model stejné velikosti, z hlediska práce s vahami, paměti a nasazení je to stále model s celkovou velikostí **35B**. Proto to není ideální první volba pro domácí GPU, pokud není k dispozici výrazně větší VRAM nebo agresivní kvantizace.

## Doporučený postup mezi domovem a školou

Pro tento projekt dává smysl následující cesta:

- doma do 12 GB VRAM: **Qwen3.5-4B**
- doma 16–24 GB VRAM: **Qwen3.5-9B**
- škola / Metacentrum: **Qwen3.5-27B**

Tento postup je praktický proto, že lze zachovat:
- stejný API tvar,
- stejnou aplikaci,
- stejný retrieval workflow,
- podobný promptovací styl,
- a změnit jen backend a velikost modelu.

## Dopad na tuto aplikaci

V kontextu tohoto MVP to znamená:

- **lokální testování** může běžet na menší variantě modelu,
- **RAG pipeline** zůstává stejná,
- při přesunu na větší GPU se mění hlavně inference backend a velikost modelu,
- není nutné předělávat ingest, chunking ani retrieval vrstvu.

To je vhodné pro vývojový postup:
1. ověřit ingest a retrieval doma,
2. ladit prompt a evaluaci na menším modelu,
3. nasadit větší model na školní infrastrukturu,
4. porovnat kvalitu odpovědí bez změny zbytku systému.

## Stručné doporučení

Pokud není znám přesný hardware předem, nejpraktičtější výchozí doporučení je:

- **do 12 GB VRAM:** Qwen3.5-4B
- **16–24 GB VRAM:** Qwen3.5-9B
- **větší školní GPU / Metacentrum:** Qwen3.5-27B

Pro většinu použití v tomto projektu je tedy nejpraktičtější cesta:

**4B / 9B doma → 27B ve škole**
