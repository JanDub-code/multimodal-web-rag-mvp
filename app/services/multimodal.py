import base64
import json
import logging
import re
from pathlib import Path

import requests

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def encode_image_file(image_path: str | Path) -> str:
    path = Path(image_path)
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def ollama_generate(
    prompt: str,
    model: str,
    image_paths: list[str] | None = None,
    timeout: int | None = None,
) -> str | None:
    payload: dict[str, object] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    resolved_images: list[str] = []
    for image_path in image_paths or []:
        path = Path(image_path)
        if path.exists() and path.is_file():
            resolved_images.append(encode_image_file(path))
    if resolved_images:
        payload["images"] = resolved_images

    try:
        response = requests.post(
            f"{settings.ollama_url}/api/generate",
            json=payload,
            timeout=timeout or settings.vision_timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response")
    except requests.ConnectionError:
        logger.error("Ollama is not reachable at %s.", settings.ollama_url)
        return None
    except Exception:
        logger.exception("Ollama request failed")
        return None


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)


def extract_json_object(text: str) -> dict | None:
    if not text:
        return None

    candidates = [text.strip()]
    candidates.extend(match.group(1).strip() for match in _JSON_FENCE_RE.finditer(text))

    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1 and last > first:
        candidates.append(text[first : last + 1].strip())

    seen: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        try:
            value = json.loads(candidate)
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            continue
    return None


def _normalize_sections(sections: object) -> list[dict]:
    normalized: list[dict] = []
    if not isinstance(sections, list):
        return normalized

    for item in sections:
        if isinstance(item, dict):
            heading = item.get("heading")
            content = item.get("content") or item.get("text")
        else:
            heading = None
            content = str(item)
        content_text = str(content or "").strip()
        heading_text = str(heading or "").strip() or None
        if content_text:
            normalized.append({"heading": heading_text, "content": content_text})
    return normalized


def _normalize_tables(tables: object) -> list[dict]:
    normalized: list[dict] = []
    if not isinstance(tables, list):
        return normalized

    for item in tables:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or item.get("name") or "").strip() or None
        columns = item.get("columns") or []
        rows = item.get("rows") or []
        if not isinstance(columns, list):
            columns = []
        if not isinstance(rows, list):
            rows = []
        normalized.append(
            {
                "title": title,
                "columns": [str(col) for col in columns if str(col).strip()],
                "rows": rows,
            }
        )
    return normalized


def extract_structured_document_from_image(
    image_path: str,
    url: str,
    title_hint: str = "",
    dom_text: str = "",
    ocr_text: str = "",
) -> tuple[dict | None, str | None]:
    if not settings.vision_extract_on_ingest:
        return None, None

    model = settings.ollama_vision_model or settings.ollama_model
    prompt = (
        "You are extracting a structured canonical document from a webpage screenshot. "
        "Return strict JSON only with keys: title, visual_summary, sections, tables. "
        "sections must be a list of objects with heading and content. "
        "tables must be a list of objects with title, columns, rows. "
        "Use the screenshot as primary evidence. Use DOM/OCR hints only to disambiguate, not to invent content. "
        "Keep sections concise and factual.\n\n"
        f"URL: {url}\n"
        f"Title hint: {title_hint or 'unknown'}\n"
        f"DOM hint: {dom_text[:settings.vision_prompt_max_context_chars]}\n"
        f"OCR hint: {ocr_text[:settings.vision_prompt_max_context_chars]}"
    )

    raw_output = ollama_generate(prompt=prompt, model=model, image_paths=[image_path])
    parsed = extract_json_object(raw_output or "")
    if not parsed:
        return None, raw_output

    sections = _normalize_sections(parsed.get("sections"))
    tables = _normalize_tables(parsed.get("tables"))
    visual_summary = str(parsed.get("visual_summary") or "").strip()
    title = str(parsed.get("title") or title_hint or "").strip() or None

    if not sections and visual_summary:
        sections = [{"heading": "Visual summary", "content": visual_summary}]

    if not sections and not tables:
        return None, raw_output

    return {
        "title": title,
        "sections": sections,
        "tables": tables,
        "visual_summary": visual_summary or None,
        "model": model,
    }, raw_output
