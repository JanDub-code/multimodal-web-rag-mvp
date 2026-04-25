from app.config import get_settings
from app.services.embeddings import resolve_embedding_base_url
from app.services.multimodal import resolve_llm_base_url

settings = get_settings()


def embedding_usage(*, used_for: list[str] | None = None, active: bool = True) -> dict:
    return {
        "provider": "ollama",
        "endpoint": f"{resolve_embedding_base_url()}/api/embed",
        "model": settings.embedding_model,
        "dimensions": settings.embedding_dimensions,
        "qdrant_collection": settings.qdrant_collection,
        "active": active,
        "used_for": used_for or ["ingest.index", "query.retrieval"],
    }


def text_usage(*, used_for: list[str] | None = None, model: str | None = None, active: bool = True) -> dict:
    return {
        "provider": "openai-compatible",
        "endpoint": f"{resolve_llm_base_url()}/chat/completions",
        "model": model or settings.llm_model,
        "active": active,
        "used_for": used_for or ["query.no_rag", "query.rag.answer"],
    }


def vision_usage(*, used_for: list[str] | None = None, model: str | None = None, active: bool | None = None) -> dict:
    selected_model = model or settings.llm_vision_model
    enabled = active if active is not None else bool(
        selected_model and (settings.vision_answer_enabled or settings.vision_extract_on_ingest)
    )
    return {
        "provider": "openai-compatible",
        "endpoint": f"{resolve_llm_base_url()}/chat/completions",
        "model": selected_model,
        "active": bool(enabled),
        "used_for": used_for or ["ingest.vision_extract", "query.rag.vision_answer"],
    }


def configured_model_usage() -> dict:
    return {
        "text": text_usage(),
        "vision": vision_usage(),
        "embedding": embedding_usage(),
    }


def query_model_usage(*, mode: str, generation_model: str | None = None, vision_used: bool = False) -> dict:
    if mode == "no-rag":
        return {
            "text": text_usage(used_for=["query.no_rag"], model=generation_model or settings.llm_model),
        }

    usage = {
        "embedding": embedding_usage(used_for=["query.retrieval"]),
    }
    if generation_model:
        usage["answer"] = text_usage(used_for=["query.rag.answer"], model=generation_model)
    if vision_used:
        usage["vision"] = vision_usage(used_for=["query.rag.vision_answer"], model=generation_model, active=True)
    return usage


def ingest_model_usage(*, embedding_used: bool = True, vision_used: bool | None = None, vision_model: str | None = None) -> dict:
    usage = {
        "embedding": embedding_usage(used_for=["ingest.index"], active=embedding_used),
    }
    if vision_used is True:
        usage["vision"] = vision_usage(used_for=["ingest.vision_extract"], model=vision_model, active=True)
    elif vision_used is None and settings.vision_extract_on_ingest:
        usage["vision"] = vision_usage(used_for=["ingest.vision_extract"], model=vision_model, active=False)
    return usage
