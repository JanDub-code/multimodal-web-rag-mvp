import base64
import json
import logging
import re
import mimetypes
from pathlib import Path

import requests

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

ANTHROPIC_GO_MODELS = {"minimax-m2.7", "minimax-m2.5"}


def resolve_opencode_go_base_url() -> str:
    return settings.opencode_go_base_url.strip().rstrip("/")


def encode_image_file(image_path: str | Path) -> str:
    path = Path(image_path)
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def _build_openai_messages(prompt: str, image_paths: list[str] | None = None) -> list[dict[str, object]]:
    content: list[dict[str, object]] = [{"type": "text", "text": prompt}]
    for image_path in image_paths or []:
        path = Path(image_path)
        if path.exists() and path.is_file():
            mime_type = mimetypes.guess_type(path.name)[0] or "image/png"
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{encode_image_file(path)}"},
                }
            )

    if len(content) == 1:
        return [{"role": "user", "content": prompt}]
    return [{"role": "user", "content": content}]


def _build_anthropic_content(prompt: str, image_paths: list[str] | None = None) -> list[dict[str, object]]:
    content: list[dict[str, object]] = [{"type": "text", "text": prompt}]
    for image_path in image_paths or []:
        path = Path(image_path)
        if not path.exists() or not path.is_file():
            continue
        media_type = mimetypes.guess_type(path.name)[0] or "image/png"
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": encode_image_file(path),
                },
            }
        )
    return content


def _normalize_go_model_id(model: str) -> str:
    return model.removeprefix("opencode-go/").strip()


def _select_go_model(model: str, image_paths: list[str] | None = None) -> str:
    if image_paths:
        return _normalize_go_model_id(settings.vision_generation_model)
    return _normalize_go_model_id(model)


def _extract_openai_text(payload: dict) -> str | None:
    choices = payload.get("choices") if isinstance(payload, dict) else None
    if not isinstance(choices, list) or not choices:
        return None
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    return content if isinstance(content, str) else None


def _extract_anthropic_text(payload: dict) -> str | None:
    content = payload.get("content") if isinstance(payload, dict) else None
    if not isinstance(content, list):
        return None
    parts = []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
            parts.append(item["text"])
    text = "\n".join(part.strip() for part in parts if part.strip()).strip()
    return text or None


def _go_headers(*, anthropic: bool = False) -> dict[str, str]:
    if not settings.opencode_api_key:
        raise RuntimeError("OPENCODE_API_KEY is not configured.")
    headers = {
        "Authorization": f"Bearer {settings.opencode_api_key}",
        "Content-Type": "application/json",
    }
    if anthropic:
        headers["x-api-key"] = settings.opencode_api_key
        headers["anthropic-version"] = "2023-06-01"
    return headers


def opencode_go_chat_generate(
    prompt: str,
    model: str,
    image_paths: list[str] | None = None,
    timeout: int | None = None,
) -> str | None:
    selected_model = _select_go_model(model, image_paths)
    base_url = resolve_opencode_go_base_url()
    anthropic = selected_model in ANTHROPIC_GO_MODELS

    if anthropic:
        endpoint = f"{base_url}/messages"
        payload: dict[str, object] = {
            "model": selected_model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": _build_anthropic_content(prompt, image_paths)}],
        }
    else:
        endpoint = f"{base_url}/chat/completions"
        payload = {
            "model": selected_model,
            "messages": _build_openai_messages(prompt, image_paths),
        }

    try:
        response = requests.post(
            endpoint,
            json=payload,
            headers=_go_headers(anthropic=anthropic),
            timeout=timeout or settings.vision_timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        return _extract_anthropic_text(data) if anthropic else _extract_openai_text(data)
    except RuntimeError as exc:
        logger.error(str(exc))
        return None
    except requests.ConnectionError:
        logger.error("OpenCode Go backend is not reachable at %s.", base_url)
        return None
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else "unknown"
        response_body = (exc.response.text or "")[:500] if exc.response is not None else ""
        logger.error("OpenCode Go request failed with status %s: %s", status_code, response_body)
        return None
    except Exception:
        logger.exception("OpenCode Go request failed")
        return None


def chat_generate(
    prompt: str,
    model: str,
    image_paths: list[str] | None = None,
    timeout: int | None = None,
) -> str | None:
    provider = settings.generation_provider.strip().lower()
    if provider not in {"opencode_go", "opencode-go"}:
        logger.error("Unsupported generation provider '%s'. Expected opencode_go.", provider)
        return None

    return opencode_go_chat_generate(prompt=prompt, model=model, image_paths=image_paths, timeout=timeout)


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

    model = settings.default_generation_model
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

    raw_output = chat_generate(prompt=prompt, model=model, image_paths=[image_path])
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
