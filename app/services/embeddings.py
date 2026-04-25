import logging
from typing import Any

import requests

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmbeddingBackendError(RuntimeError):
    """Raised when the configured embedding backend cannot return valid vectors."""


def resolve_embedding_base_url() -> str:
    return settings.embedding_base_url.strip().rstrip("/")


def _coerce_vector(value: Any, *, index: int) -> list[float]:
    if not isinstance(value, list) or not value:
        raise EmbeddingBackendError(f"Embedding response item {index} is not a non-empty vector.")
    try:
        return [float(item) for item in value]
    except (TypeError, ValueError) as exc:
        raise EmbeddingBackendError(f"Embedding response item {index} contains a non-numeric value.") from exc


def _extract_embeddings(payload: dict[str, Any], expected_count: int) -> list[list[float]]:
    vectors = payload.get("embeddings")
    if not isinstance(vectors, list):
        raise EmbeddingBackendError("Embedding response does not contain an 'embeddings' array.")
    if len(vectors) != expected_count:
        raise EmbeddingBackendError(
            f"Embedding response returned {len(vectors)} vectors for {expected_count} inputs."
        )
    return [_coerce_vector(vector, index=idx) for idx, vector in enumerate(vectors)]


def embed_texts(
    texts: list[str],
    *,
    model: str | None = None,
    dimensions: int | None = None,
    timeout: int | None = None,
) -> list[list[float]]:
    if not texts:
        return []

    selected_model = model or settings.embedding_model
    selected_dimensions = dimensions if dimensions is not None else settings.embedding_dimensions
    payload: dict[str, Any] = {
        "model": selected_model,
        "input": texts,
    }
    if selected_dimensions:
        payload["dimensions"] = selected_dimensions

    endpoint = f"{resolve_embedding_base_url()}/api/embed"
    try:
        response = requests.post(
            endpoint,
            json=payload,
            timeout=timeout or settings.embedding_timeout_seconds,
        )
        response.raise_for_status()
    except requests.ConnectionError as exc:
        raise EmbeddingBackendError(f"Ollama embedding backend is not reachable at {endpoint}.") from exc
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else "unknown"
        response_body = (exc.response.text or "")[:500] if exc.response is not None else ""
        raise EmbeddingBackendError(
            f"Ollama embedding request failed with status {status_code}: {response_body}"
        ) from exc
    except requests.RequestException as exc:
        raise EmbeddingBackendError(f"Ollama embedding request failed: {exc}") from exc

    try:
        return _extract_embeddings(response.json(), expected_count=len(texts))
    except ValueError as exc:
        raise EmbeddingBackendError("Ollama embedding response is not valid JSON.") from exc


def embed_query(query: str) -> list[float]:
    return embed_texts([query])[0]


def get_ollama_tags(timeout: int = 3) -> dict[str, Any]:
    response = requests.get(f"{resolve_embedding_base_url()}/api/tags", timeout=timeout)
    response.raise_for_status()
    return response.json()


def get_ollama_running_models(timeout: int = 3) -> dict[str, Any]:
    response = requests.get(f"{resolve_embedding_base_url()}/api/ps", timeout=timeout)
    response.raise_for_status()
    return response.json()
