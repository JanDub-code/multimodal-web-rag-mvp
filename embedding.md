# Embedding Model Notes

## Current model

The app currently uses:

```text
sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

Runtime:

- Provider: FastEmbed / ONNX
- Device target: CPU
- Dimensions: 384
- Approx model size: 0.22 GB
- Qdrant collection: `chunks_fastembed_multilingual_minilm_384`
- Warmed on API startup and cached in the `fastembed_cache` Docker volume

This is a good practical baseline: multilingual, small, fast, and cheap to run locally.

## Local CPU measurements

Measured inside the `api` container with the current FastEmbed stack. The model download/init time is shown separately from warm embedding throughput. Download time depends heavily on HuggingFace/network speed and is not normal per-query runtime once cached.

| Model | Dim | Size | Init/download observed | 1 short text | Batch 30 | Relative ingest speed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | 384 | 0.22 GB | 1.3 s cached init | 8 ms | 714 ms, 24 ms/text | 1.0x |
| `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` | 768 | 1.0 GB | 145 s first download | 17 ms | 2157 ms, 72 ms/text | ~3.0x slower |
| `intfloat/multilingual-e5-large` | 1024 | 2.24 GB | 282 s first download | 93 ms | 8659 ms, 289 ms/text | ~12x slower |

For RAG query-time retrieval, even the bigger models are still small next to generation latency:

- MiniLM query embedding is roughly 8-15 ms warm.
- MPNet query embedding is roughly 17 ms warm, so the query-time hit is tiny.
- E5-large query embedding was roughly 93 ms warm, still usable, but the ingest cost and RAM/model size are much higher.

## Candidate assessment

### Keep MiniLM

Best if the priority is speed, low memory, and frictionless local CPU operation.

Pros:

- Very fast ingest and query embedding.
- Small model, quick startup once cached.
- Already deployed and indexed.

Cons:

- Retrieval quality is only decent. For nuanced Czech/multilingual semantic matching, it may miss more than stronger multilingual models.

### Upgrade to multilingual MPNet

Recommended balanced upgrade:

```text
sentence-transformers/paraphrase-multilingual-mpnet-base-v2
```

Pros:

- Multilingual and likely better semantic retrieval than MiniLM.
- Still CPU-compatible through FastEmbed/ONNX.
- Query-time slowdown is basically negligible compared with LLM generation.
- Does not require E5-style `query:` / `passage:` prefix changes.

Cons:

- About 3x slower for batch embedding during ingest.
- Larger cache/model footprint.
- Requires a new Qdrant collection and reingest because dimensions change from 384 to 768.

With the current dataset size, this cost is trivial. The database currently has about 100 chunks, so reembedding should be quick after the first model download.

### E5-large

High-quality option, but not the best next step for this MVP:

```text
intfloat/multilingual-e5-large
```

Pros:

- Strong multilingual retrieval candidate.
- 1024-dimensional embeddings can improve ranking quality.

Cons:

- About 12x slower for batch ingest in local measurement.
- Much larger first download and cache footprint.
- Ideally wants query/document prefixes (`query: ...`, `passage: ...`) for best behavior, which means a slightly more opinionated pipeline change.

## Recommendation

Use `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` if we want a quality bump without making the system feel heavy.

Expected impact:

- RAG answer latency: almost unchanged, because generation dominates.
- RAG retrieval latency: maybe +10 ms to +50 ms in normal warm operation.
- Ingest embedding step: roughly 3x slower than the current MiniLM model.
- First deployment: one-time model download can take a couple of minutes unless already cached.

Do not switch to E5-large yet unless retrieval quality clearly becomes the bottleneck and we are willing to tune the embedding pipeline.

## Migration notes

Changing embedding dimensions requires a fresh Qdrant collection or a full reindex.

For MPNet:

```env
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-mpnet-base-v2
EMBEDDING_DIMENSIONS=768
QDRANT_COLLECTION=chunks_fastembed_multilingual_mpnet_768
```

Then reingest sources so all chunks are embedded into the new collection.
