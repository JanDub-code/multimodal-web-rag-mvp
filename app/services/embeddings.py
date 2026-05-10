from functools import lru_cache
from typing import Iterable

from app.config import get_settings

settings = get_settings()


class EmbeddingBackendError(RuntimeError):
    pass


@lru_cache
def _embedding_model(model_name: str):
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=model_name)


def embed_texts(texts: list[str], *, model: str | None = None) -> list[list[float]]:
    if not texts:
        return []

    selected_model = model or settings.embedding_model
    try:
        vectors: Iterable = _embedding_model(selected_model).embed(texts)
        result = [[float(value) for value in vector] for vector in vectors]
    except Exception as exc:
        raise EmbeddingBackendError(f"FastEmbed failed for model '{selected_model}': {exc}") from exc

    if len(result) != len(texts):
        raise EmbeddingBackendError(f"FastEmbed returned {len(result)} vectors for {len(texts)} texts.")
    if result and len(result[0]) != settings.embedding_dimensions:
        raise EmbeddingBackendError(
            f"FastEmbed model '{selected_model}' returned dimension {len(result[0])}, "
            f"expected {settings.embedding_dimensions}."
        )
    return result


def embed_query(query: str) -> list[float]:
    return embed_texts([query])[0]
