#!/usr/bin/env python3
import argparse
import json
import re
import statistics
import time
from pathlib import Path
from typing import Any

from qdrant_client.http import models as qmodels

from app.config import get_settings
from app.db.models import Chunk, Document
from app.db.session import SessionLocal
from app.services.embeddings import embed_texts, get_ollama_running_models, get_ollama_tags
from app.services.retrieval import ensure_collection, get_qdrant

DEFAULT_MODELS = ["qwen3-embedding:0.6b", "qwen3-embedding:4b", "qwen3-embedding:8b"]
DEFAULT_DIMENSIONS = {
    "qwen3-embedding": 4096,
    "qwen3-embedding:latest": 4096,
    "qwen3-embedding:0.6b": 1024,
    "qwen3-embedding:4b": 2560,
    "qwen3-embedding:8b": 4096,
}


def _safe_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_").lower()


def _batched(items: list[Any], batch_size: int) -> list[list[Any]]:
    return [items[idx : idx + batch_size] for idx in range(0, len(items), batch_size)]


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * percentile)))
    return ordered[index]


def _load_chunks(limit: int | None) -> list[dict]:
    with SessionLocal() as db:
        query = (
            db.query(Chunk, Document)
            .join(Document, Chunk.doc_id == Document.id)
            .order_by(Chunk.id.asc())
        )
        if limit:
            query = query.limit(limit)
        rows = []
        for chunk, document in query.all():
            rows.append(
                {
                    "chunk_id": chunk.id,
                    "doc_id": document.id,
                    "source_id": document.source_id,
                    "url": document.url,
                    "text": chunk.text,
                    "chunk_type": chunk.chunk_type,
                    "citations_ref": chunk.citations_ref,
                }
            )
        return rows


def _load_queries(path: str | None) -> list[dict]:
    if not path:
        return [
            {
                "query": "Jak system uklada evidence artefakty?",
                "expected_url_contains": "",
            },
            {
                "query": "How does the RAG query flow use citations?",
                "expected_url_contains": "",
            },
        ]

    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError("Query file must contain a JSON array.")
    for item in data:
        if not isinstance(item, dict) or not item.get("query"):
            raise ValueError("Every query item must be an object with a non-empty 'query'.")
    return data


def _expected_match(query_item: dict, hit: Any) -> bool:
    payload = hit.payload or {}
    expected_chunk_id = query_item.get("expected_chunk_id")
    if expected_chunk_id is not None and str(getattr(hit, "id", "")) == str(expected_chunk_id):
        return True

    expected_doc_id = query_item.get("expected_doc_id")
    if expected_doc_id is not None and str(payload.get("doc_id")) == str(expected_doc_id):
        return True

    expected_source_id = query_item.get("expected_source_id")
    if expected_source_id is not None and str(payload.get("source_id")) == str(expected_source_id):
        return True

    expected_url_contains = str(query_item.get("expected_url_contains") or "").strip()
    return bool(expected_url_contains and expected_url_contains in str(payload.get("url") or ""))


def _has_expectation(query_item: dict) -> bool:
    return any(
        query_item.get(key)
        for key in ("expected_chunk_id", "expected_doc_id", "expected_source_id", "expected_url_contains")
    )


def _resolve_dimensions(model: str, dimensions: str) -> int | None:
    if dimensions == "native":
        return None
    if dimensions == "auto":
        return DEFAULT_DIMENSIONS.get(model)
    return int(dimensions)


def _upsert_model_collection(
    *,
    model: str,
    dimensions: int | None,
    collection_name: str,
    chunks: list[dict],
    batch_size: int,
) -> int:
    client = get_qdrant()
    vector_size = None
    for batch in _batched(chunks, batch_size):
        vectors = embed_texts([row["text"] for row in batch], model=model, dimensions=dimensions)
        if not vectors:
            continue
        if vector_size is None:
            vector_size = len(vectors[0])
            ensure_collection(vector_size=vector_size, collection_name=collection_name)
        points = []
        for row, vector in zip(batch, vectors, strict=True):
            points.append(
                qmodels.PointStruct(
                    id=int(row["chunk_id"]),
                    vector=vector,
                    payload={
                        "chunk_id": row["chunk_id"],
                        "doc_id": row["doc_id"],
                        "source_id": row["source_id"],
                        "url": row["url"],
                        "text": row["text"],
                        "chunk_type": row.get("chunk_type", "text"),
                        "citations_ref": row["citations_ref"],
                        "benchmark_model": model,
                    },
                )
            )
        client.upsert(collection_name=collection_name, points=points)
    return vector_size or 0


def _measure_queries(
    *,
    model: str,
    dimensions: int | None,
    collection_name: str,
    queries: list[dict],
    top_k: int,
) -> dict:
    client = get_qdrant()
    latencies_ms = []
    scored = 0
    hits = 0
    reciprocal_ranks = []

    for query_item in queries:
        started = time.perf_counter()
        query_vector = embed_texts([query_item["query"]], model=model, dimensions=dimensions)[0]
        results = client.search(collection_name=collection_name, query_vector=query_vector, limit=top_k)
        latencies_ms.append((time.perf_counter() - started) * 1000)

        if not _has_expectation(query_item):
            continue

        scored += 1
        rank = None
        for idx, hit in enumerate(results, start=1):
            if _expected_match(query_item, hit):
                rank = idx
                break
        if rank is not None:
            hits += 1
            reciprocal_ranks.append(1 / rank)
        else:
            reciprocal_ranks.append(0.0)

    return {
        "query_count": len(queries),
        "scored_query_count": scored,
        "hit_at_k": (hits / scored) if scored else None,
        "mrr_at_k": statistics.mean(reciprocal_ranks) if reciprocal_ranks else None,
        "latency_p50_ms": _percentile(latencies_ms, 0.50),
        "latency_p95_ms": _percentile(latencies_ms, 0.95),
    }


def _model_size_from_tags(model: str) -> int | None:
    try:
        tags = get_ollama_tags()
    except Exception:
        return None
    for item in tags.get("models", []):
        if item.get("model") == model or item.get("name") == model:
            return item.get("size")
    return None


def _running_model_stats(model: str) -> dict:
    try:
        payload = get_ollama_running_models()
    except Exception:
        return {}
    for item in payload.get("models", []):
        if item.get("model") == model or item.get("name") == model:
            return {
                "loaded_size_bytes": item.get("size"),
                "loaded_vram_bytes": item.get("size_vram"),
                "context_length": item.get("context_length"),
            }
    return {}


def _ollama_process_stats() -> dict:
    try:
        import psutil
    except Exception:
        return {}

    rss = 0
    cpu = 0.0
    found = 0
    for proc in psutil.process_iter(["name", "cmdline", "memory_info", "cpu_percent"]):
        try:
            name = proc.info.get("name") or ""
            cmdline = " ".join(proc.info.get("cmdline") or [])
            if "ollama" not in name.lower() and "ollama" not in cmdline.lower():
                continue
            found += 1
            rss += proc.info["memory_info"].rss
            cpu += float(proc.info.get("cpu_percent") or 0.0)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return {"ollama_processes": found, "ollama_rss_bytes": rss or None, "ollama_cpu_percent": cpu if found else None}


def _bytes_to_mb(value: int | None) -> str:
    if value is None:
        return "n/a"
    return f"{value / 1024 / 1024:.0f}"


def _number(value: float | None, suffix: str = "") -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}{suffix}"


def _markdown_table(results: list[dict], top_k: int) -> str:
    lines = [
        f"| Model | Dimenze | Hit@{top_k} | MRR@{top_k} | p50 ms | p95 ms | Model MB | Loaded RAM MB | VRAM MB | CPU % | Poznamka |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in results:
        lines.append(
            "| {model} | {dimensions} | {hit} | {mrr} | {p50} | {p95} | {model_mb} | {ram_mb} | {vram_mb} | {cpu} | {note} |".format(
                model=row["model"],
                dimensions=row["vector_size"] or "n/a",
                hit=_number(row["metrics"]["hit_at_k"]),
                mrr=_number(row["metrics"]["mrr_at_k"]),
                p50=_number(row["metrics"]["latency_p50_ms"]),
                p95=_number(row["metrics"]["latency_p95_ms"]),
                model_mb=_bytes_to_mb(row.get("model_size_bytes")),
                ram_mb=_bytes_to_mb(row.get("loaded_size_bytes") or row.get("ollama_rss_bytes")),
                vram_mb=_bytes_to_mb(row.get("loaded_vram_bytes")),
                cpu=_number(row.get("ollama_cpu_percent")),
                note=row.get("note") or "",
            )
        )
    return "\n".join(lines)


def _update_readme(path: str, table: str) -> None:
    readme_path = Path(path)
    content = readme_path.read_text(encoding="utf-8")
    start = "<!-- EMBEDDING_BENCHMARK_TABLE_START -->"
    end = "<!-- EMBEDDING_BENCHMARK_TABLE_END -->"
    replacement = f"{start}\n{table}\n{end}"
    if start not in content or end not in content:
        content = f"{content.rstrip()}\n\n## Embedding benchmark\n\n{replacement}\n"
    else:
        content = re.sub(f"{start}.*?{end}", replacement, content, flags=re.DOTALL)
    readme_path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark Ollama embedding models against local chunks.")
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--queries", help="JSON file with query expectations.")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--limit-chunks", type=int)
    parser.add_argument("--dimensions", default="auto", help="'auto', 'native', or an integer dimension.")
    parser.add_argument("--readme-update", help="Optional README path to update with the benchmark table.")
    args = parser.parse_args()

    settings = get_settings()
    chunks = _load_chunks(args.limit_chunks)
    if not chunks:
        raise SystemExit("No chunks found in PostgreSQL. Ingest local data before benchmarking.")
    queries = _load_queries(args.queries)

    results = []
    for model in args.models:
        dimensions = _resolve_dimensions(model, args.dimensions)
        dimension_label = dimensions if dimensions is not None else "native"
        collection_name = f"{settings.qdrant_collection}_bench_{_safe_name(model)}_{dimension_label}"
        started = time.perf_counter()
        vector_size = _upsert_model_collection(
            model=model,
            dimensions=dimensions,
            collection_name=collection_name,
            chunks=chunks,
            batch_size=args.batch_size,
        )
        metrics = _measure_queries(
            model=model,
            dimensions=dimensions,
            collection_name=collection_name,
            queries=queries,
            top_k=args.top_k,
        )
        row = {
            "model": model,
            "requested_dimensions": dimensions,
            "vector_size": vector_size,
            "collection": collection_name,
            "metrics": metrics,
            "model_size_bytes": _model_size_from_tags(model),
            "index_seconds": time.perf_counter() - started,
            **_running_model_stats(model),
            **_ollama_process_stats(),
        }
        if metrics["scored_query_count"] == 0:
            row["note"] = "quality n/a: add expected_* fields to query JSON"
        results.append(row)

    table = _markdown_table(results, args.top_k)
    print(table)
    if args.readme_update:
        _update_readme(args.readme_update, table)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
