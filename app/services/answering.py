import logging
from pathlib import Path

from app.config import get_settings
from app.services.multimodal import ollama_generate

logger = logging.getLogger(__name__)
settings = get_settings()


_OLLAMA_UNAVAILABLE_MSG = (
    "LLM (Ollama) is not available. Start Ollama with the '{}' model to get generated answers."
)


def _collect_screenshot_paths(retrieved: list[dict]) -> list[str]:
    image_paths: list[str] = []
    for item in retrieved:
        citations = item.get("citations") or {}
        evidence_items = citations.get("evidence_items") or []
        for evidence in evidence_items:
            if evidence.get("type") != "screenshot":
                continue
            storage_uri = str(evidence.get("storage_uri") or "").strip()
            if not storage_uri:
                continue
            if storage_uri in image_paths:
                continue
            if not Path(storage_uri).exists():
                continue
            image_paths.append(storage_uri)
            if len(image_paths) >= settings.vision_max_images:
                return image_paths
    return image_paths


def answer_no_rag(query: str) -> str:
    prompt = f"Answer briefly and clearly:\n{query}"
    model_output = ollama_generate(prompt=prompt, model=settings.ollama_model, image_paths=None, timeout=60)
    if model_output:
        return model_output.strip()
    return _OLLAMA_UNAVAILABLE_MSG.format(settings.ollama_model)


def answer_rag(query: str, retrieved: list[dict]) -> dict:
    if not retrieved:
        return {
            "answer": "No relevant documents found for this query.",
            "citations": [],
        }

    context_lines = []
    citations = []
    for idx, item in enumerate(retrieved, start=1):
        context_lines.append(f"[{idx}] {item['text']}")
        citations.append(
            {
                "index": idx,
                "url": item.get("url"),
                "score": item.get("score"),
                "evidence": item.get("citations"),
            }
        )

    context = "\n\n".join(context_lines)
    prompt = (
        "Use only provided context. If unsupported, say so. Include references [n]. "
        "If screenshots are attached, use them only as supporting evidence for the cited passages.\n\n"
        f"Question: {query}\n\nContext:\n{context}"
    )

    image_paths = _collect_screenshot_paths(retrieved) if settings.vision_answer_enabled else []
    model_name = (settings.ollama_vision_model or settings.ollama_model) if image_paths else settings.ollama_model
    model_output = ollama_generate(
        prompt=prompt,
        model=model_name,
        image_paths=image_paths or None,
        timeout=max(60, settings.vision_timeout_seconds),
    )
    if not model_output:
        return {
            "answer": _OLLAMA_UNAVAILABLE_MSG.format(model_name),
            "citations": citations,
        }
    return {"answer": model_output.strip(), "citations": citations}
