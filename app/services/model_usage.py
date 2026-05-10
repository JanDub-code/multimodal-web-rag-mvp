from app.config import get_settings
from app.services.multimodal import resolve_opencode_go_base_url

settings = get_settings()


def _resolve_text_endpoint(model: str | None) -> str:
    return resolve_opencode_go_base_url()


def retrieval_usage(*, used_for: list[str] | None = None, active: bool = True) -> dict:
    return {
        "provider": "fastembed-qdrant",
        "endpoint": settings.qdrant_url,
        "model": settings.embedding_model,
        "dimensions": settings.embedding_dimensions,
        "qdrant_collection": settings.qdrant_collection,
        "active": active,
        "used_for": used_for or ["query.retrieval"],
    }


def text_usage(*, used_for: list[str] | None = None, model: str | None = None, active: bool = True) -> dict:
    return {
        "provider": "opencode",
        "endpoint": _resolve_text_endpoint(model),
        "model": model or settings.default_generation_model,
        "active": active,
        "used_for": used_for or ["query.no_rag", "query.rag.answer"],
    }


def vision_usage(*, used_for: list[str] | None = None, model: str | None = None, active: bool | None = None) -> dict:
    selected_model = model or settings.vision_generation_model
    enabled = active if active is not None else bool(selected_model and settings.vision_extract_on_ingest)
    return {
        "provider": "opencode",
        "endpoint": resolve_opencode_go_base_url(),
        "model": selected_model,
        "active": bool(enabled),
        "used_for": used_for or ["ingest.vision_extract", "query.rag.vision_answer"],
    }


def configured_model_usage() -> dict:
    return {
        "text": text_usage(),
        "vision": vision_usage(),
        "retrieval": retrieval_usage(),
    }


def query_model_usage(*, mode: str, generation_model: str | None = None, vision_used: bool = False) -> dict:
    if mode == "no-rag":
        return {
            "text": text_usage(used_for=["query.no_rag"], model=generation_model or settings.default_generation_model),
        }

    usage = {
        "retrieval": retrieval_usage(used_for=["query.retrieval"]),
    }
    if generation_model:
        usage["answer"] = text_usage(used_for=["query.rag.answer"], model=generation_model)
    if vision_used:
        usage["vision"] = vision_usage(used_for=["query.rag.vision_answer"], active=True)
    return usage


def ingest_model_usage(*, index_used: bool = True, vision_used: bool | None = None, vision_model: str | None = None) -> dict:
    usage = {
        "retrieval_index": {
            "provider": "fastembed-qdrant",
            "endpoint": settings.qdrant_url,
            "model": settings.embedding_model,
            "dimensions": settings.embedding_dimensions,
            "qdrant_collection": settings.qdrant_collection,
            "active": index_used,
            "used_for": ["ingest.index"],
        },
    }
    if vision_used is True:
        usage["vision"] = vision_usage(used_for=["ingest.vision_extract"], model=vision_model, active=True)
    elif vision_used is None and settings.vision_extract_on_ingest:
        usage["vision"] = vision_usage(used_for=["ingest.vision_extract"], model=vision_model, active=False)
    return usage
