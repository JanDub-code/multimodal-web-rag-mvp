import json
import logging
import os
import re
import unicodedata
from functools import lru_cache
from typing import Any

from app.config import get_settings
from app.services.embeddings import embed_texts

logger = logging.getLogger(__name__)
settings = get_settings()

_STOPWORDS = {
    "a",
    "aby",
    "aj",
    "ale",
    "anebo",
    "ani",
    "ano",
    "asi",
    "bez",
    "by",
    "byl",
    "byla",
    "byli",
    "bylo",
    "byt",
    "co",
    "cz",
    "do",
    "i",
    "jak",
    "jako",
    "jsem",
    "jsi",
    "jsou",
    "kde",
    "ktera",
    "ktery",
    "ktere",
    "ma",
    "me",
    "mi",
    "mu",
    "na",
    "nad",
    "ne",
    "nebo",
    "nejaky",
    "o",
    "od",
    "po",
    "pod",
    "pro",
    "s",
    "se",
    "sezenu",
    "si",
    "tak",
    "takze",
    "ten",
    "tento",
    "to",
    "u",
    "v",
    "ve",
    "vy",
    "z",
    "za",
    "ze",
}


def _normalize_text_for_matching(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


def _extract_focus_terms(text: str) -> list[str]:
    normalized = _normalize_text_for_matching(text)
    tokens = re.findall(r"\w+", normalized)
    return [token for token in tokens if len(token) >= 5 and token not in _STOPWORDS and not token.isdigit()]


def _collect_text_terms(text: str) -> set[str]:
    return set(_extract_focus_terms(text))


def _count_lexical_hits(query_terms: list[str], text_terms: set[str]) -> int:
    hits = 0
    for query_term in query_terms:
        if any(
            text_term == query_term
            or text_term.startswith(query_term)
            or query_term.startswith(text_term)
            or len(os.path.commonprefix([query_term, text_term])) >= 6
            for text_term in text_terms
        ):
            hits += 1
    return hits


def _rerank_and_deduplicate_results(query: str, rows: list[dict], top_k: int) -> list[dict]:
    query_terms = _extract_focus_terms(query)
    any_lexical_match = False
    for row in rows:
        text_terms = _collect_text_terms(row.get("text", ""))
        lexical_hits = _count_lexical_hits(query_terms, text_terms) if query_terms else 0
        row["lexical_hits"] = lexical_hits
        row["score_vector"] = row["score"]
        row["score"] = float(row["score"]) + min(0.18, lexical_hits * 0.09)
        any_lexical_match = any_lexical_match or lexical_hits > 0

    filtered_rows = rows
    if query_terms and any_lexical_match:
        filtered_rows = [row for row in rows if row["lexical_hits"] > 0]

    filtered_rows.sort(key=lambda row: (row["score"], row["score_vector"]), reverse=True)

    deduplicated: list[dict] = []
    seen_keys: set[tuple[int | None, str]] = set()
    for row in filtered_rows:
        dedup_key = (row.get("doc_id"), row.get("url", ""))
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)
        deduplicated.append(row)
        if len(deduplicated) >= top_k:
            break

    return deduplicated


def _vector_to_list(vector: Any) -> list[float]:
    if hasattr(vector, "tolist"):
        return vector.tolist()
    return list(vector)


class QdrantVectorSizeMismatchError(RuntimeError):
    pass


def _extract_collection_vector_size(collection_info: Any) -> int | None:
    config = getattr(collection_info, "config", None)
    params = getattr(config, "params", None)
    vectors_config = getattr(params, "vectors", None)

    if vectors_config is None and isinstance(collection_info, dict):
        vectors_config = (
            collection_info.get("config", {})
            .get("params", {})
            .get("vectors")
        )

    if vectors_config is None:
        return None

    if isinstance(vectors_config, dict):
        if "size" in vectors_config:
            return int(vectors_config["size"])
        for value in vectors_config.values():
            if isinstance(value, dict) and "size" in value:
                return int(value["size"])
            size = getattr(value, "size", None)
            if size is not None:
                return int(size)
        return None

    size = getattr(vectors_config, "size", None)
    return int(size) if size is not None else None


@lru_cache
def get_qdrant() -> Any:
    from qdrant_client import QdrantClient

    return QdrantClient(url=settings.qdrant_url)


def ensure_collection(vector_size: int, collection_name: str | None = None) -> None:
    collection = collection_name or settings.qdrant_collection
    client = get_qdrant()
    existing = [c.name for c in client.get_collections().collections]
    if collection in existing:
        collection_info = client.get_collection(collection_name=collection)
        existing_size = _extract_collection_vector_size(collection_info)
        if existing_size is not None and existing_size != vector_size:
            raise QdrantVectorSizeMismatchError(
                f"Qdrant collection '{collection}' has vector size {existing_size}, "
                f"but embedding model '{settings.embedding_model}' returned size {vector_size}. "
                "Use a new QDRANT_COLLECTION value or reingest data into a collection with matching dimensions."
            )
        return

    from qdrant_client.http import models as qmodels

    client.create_collection(
        collection_name=collection,
        vectors_config=qmodels.VectorParams(size=vector_size, distance=qmodels.Distance.COSINE),
    )


def upsert_chunk_vectors(rows: list[dict]) -> None:
    from qdrant_client.http import models as qmodels

    if not rows:
        return
    vectors = embed_texts([r["text"] for r in rows])
    ensure_collection(vector_size=len(vectors[0]))
    points = []
    for idx, row in enumerate(rows):
        points.append(
            qmodels.PointStruct(
                id=int(row["chunk_id"]),
                vector=_vector_to_list(vectors[idx]),
                payload={
                    "chunk_id": row["chunk_id"],
                    "doc_id": row["doc_id"],
                    "source_id": row["source_id"],
                    "url": row["url"],
                    "text": row["text"],
                    "chunk_type": row.get("chunk_type", "text"),
                    "citations_ref": row["citations_ref"],
                    "embedding_model": settings.embedding_model,
                    "embedding_dimensions": len(vectors[idx]),
                },
            )
        )
    get_qdrant().upsert(collection_name=settings.qdrant_collection, points=points)


def delete_vectors_by_chunk_ids(chunk_ids: list[int]) -> None:
    """Remove vectors from Qdrant by their point IDs (chunk IDs)."""
    from qdrant_client.http import models as qmodels

    if not chunk_ids:
        return
    try:
        get_qdrant().delete(
            collection_name=settings.qdrant_collection,
            points_selector=qmodels.PointIdsList(points=chunk_ids),
        )
        logger.info("Deleted %d vectors from Qdrant", len(chunk_ids))
    except Exception:
        logger.exception("Failed to delete vectors from Qdrant")


def search_top_k(query: str, top_k: int = 5, min_score: float | None = None) -> list[dict]:
    try:
        from qdrant_client.http.exceptions import UnexpectedResponse
    except ModuleNotFoundError:  # pragma: no cover - test/runtime fallback when qdrant extras are unavailable
        class UnexpectedResponse(Exception):
            status_code = None


    if min_score is None:
        min_score = settings.retrieval_min_score

    query_vec = _vector_to_list(embed_texts([query])[0])
    raw_limit = max(top_k * 5, top_k)
    try:
        hits = get_qdrant().search(
            collection_name=settings.qdrant_collection,
            query_vector=query_vec,
            limit=raw_limit,
        )
    except UnexpectedResponse as exc:
        if exc.status_code == 404:
            logger.warning("Qdrant collection '%s' does not exist yet — returning empty results", settings.qdrant_collection)
            return []
        raise
    results = []
    for hit in hits:
        score = float(hit.score)
        if score < min_score:
            logger.debug("Skipping hit with score %.4f (threshold %.4f)", score, min_score)
            continue
        payload = hit.payload or {}
        raw_chunk_id = getattr(hit, "id", None)
        if raw_chunk_id is None:
            raw_chunk_id = payload.get("chunk_id")
        try:
            chunk_id = int(raw_chunk_id) if raw_chunk_id is not None else None
        except (TypeError, ValueError):
            chunk_id = None
        citations = payload.get("citations_ref")
        if isinstance(citations, str):
            try:
                citations = json.loads(citations)
            except json.JSONDecodeError:
                citations = {"raw": citations}
        results.append(
            {
                "score": score,
                "chunk_id": chunk_id,
                "doc_id": payload.get("doc_id"),
                "source_id": payload.get("source_id"),
                "text": payload.get("text", ""),
                "url": payload.get("url", ""),
                "chunk_type": payload.get("chunk_type", "text"),
                "citations": citations,
            }
        )

    reranked = _rerank_and_deduplicate_results(query=query, rows=results, top_k=top_k)
    logger.info(
        "Query returned %d results above threshold %.2f (from %d hits, %d candidates after rerank)",
        len(reranked),
        min_score,
        len(hits),
        len(results),
    )
    return reranked
