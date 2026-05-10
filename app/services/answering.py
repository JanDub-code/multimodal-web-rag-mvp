import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.services.audit import write_audit
from app.services.model_usage import query_model_usage
from app.services.multimodal import chat_generate

logger = logging.getLogger(__name__)
settings = get_settings()


_GENERATION_UNAVAILABLE_MSG = (
    "OpenCode generation is not available. Check the configured endpoint, API key and the '{}' model."
)


def _format_conversation_history(conversation_history: list[dict] | None) -> str:
    lines: list[str] = []
    for message in (conversation_history or [])[-8:]:
        role = str(message.get("role") or "").strip().lower()
        if role == "ai":
            role = "assistant"
        if role not in {"user", "assistant"}:
            continue

        content = str(message.get("content") or "").strip()
        if not content:
            continue
        if len(content) > 1200:
            content = f"{content[:1200].rstrip()}..."

        label = "User" if role == "user" else "Assistant"
        lines.append(f"{label}: {content}")

    if not lines:
        return ""
    return "Previous conversation:\n" + "\n".join(lines)


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


def _audit_model_call(
    db: Session | None,
    *,
    user_id: int | None,
    model: str,
    context: str,
    status: str,
    image_count: int,
    prompt_chars: int,
) -> None:
    if db is None:
        return
    write_audit(
        db,
        action="model.call",
        object_ref=f"model:{model}",
        user_id=user_id,
        metadata={
            "context": context,
            "status": status,
            "model": model,
            "image_count": image_count,
            "prompt_chars": prompt_chars,
        },
    )


def answer_no_rag(
    query: str,
    db: Session | None = None,
    user_id: int | None = None,
    model: str | None = None,
    conversation_history: list[dict] | None = None,
) -> str:
    history_block = _format_conversation_history(conversation_history)
    prompt = "Answer briefly and clearly."
    if history_block:
        prompt = f"{prompt}\n\n{history_block}"
    prompt = f"{prompt}\n\nCurrent question:\n{query}"
    model_name = model or settings.default_generation_model
    model_output = chat_generate(prompt=prompt, model=model_name, image_paths=None, timeout=60)
    _audit_model_call(
        db,
        user_id=user_id,
        model=model_name,
        context="query.no_rag",
        status="ok" if model_output else "unavailable_or_error",
        image_count=0,
        prompt_chars=len(prompt),
    )
    if model_output:
        return model_output.strip()
    return _GENERATION_UNAVAILABLE_MSG.format(model_name)


def answer_rag(
    query: str,
    retrieved: list[dict],
    db: Session | None = None,
    user_id: int | None = None,
    model: str | None = None,
    conversation_history: list[dict] | None = None,
) -> dict:
    if not retrieved:
        return {
            "answer": "No relevant documents found for this query.",
            "citations": [],
            "model_usage": query_model_usage(mode="rag", generation_model=None, vision_used=False),
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
                "source_id": item.get("source_id"),
                "doc_id": item.get("doc_id"),
                "chunk_id": item.get("chunk_id"),
                "chunk_type": item.get("chunk_type"),
                "evidence": item.get("citations"),
            }
        )

    context = "\n\n".join(context_lines)
    history_block = _format_conversation_history(conversation_history)
    prompt_prefix = (
        "Use only provided context. If unsupported, say so. Include references [n]. "
        "If screenshots are attached, use them only as supporting evidence for the cited passages."
    )
    if history_block:
        prompt_prefix = f"{prompt_prefix}\n\n{history_block}"
    prompt = f"{prompt_prefix}\n\nCurrent question: {query}\n\nContext:\n{context}"

    image_paths = _collect_screenshot_paths(retrieved)
    model_name = model or settings.default_generation_model
    model_output = chat_generate(
        prompt=prompt,
        model=model_name,
        image_paths=image_paths or None,
        timeout=max(60, settings.vision_timeout_seconds),
    )
    _audit_model_call(
        db,
        user_id=user_id,
        model=settings.vision_generation_model if image_paths else model_name,
        context="query.rag",
        status="ok" if model_output else "unavailable_or_error",
        image_count=len(image_paths),
        prompt_chars=len(prompt),
    )
    if not model_output:
        return {
            "answer": _GENERATION_UNAVAILABLE_MSG.format(model_name),
            "citations": citations,
            "model_usage": query_model_usage(mode="rag", generation_model=model_name, vision_used=bool(image_paths)),
        }
    return {
        "answer": model_output.strip(),
        "citations": citations,
        "model_usage": query_model_usage(mode="rag", generation_model=model_name, vision_used=bool(image_paths)),
    }
