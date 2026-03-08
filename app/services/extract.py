import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


def _sections_from_text(text: str) -> list[dict]:
    sections = []
    for paragraph in [p.strip() for p in text.split("\n") if p.strip()]:
        sections.append({"heading": None, "content": paragraph})
    return sections


def _normalize_sections(sections: list[dict] | None, text: str) -> list[dict]:
    raw_sections = sections if sections else _sections_from_text(text)
    normalized = []
    for section in raw_sections:
        heading = str(section.get("heading") or "").strip() or None
        content = str(section.get("content") or "").strip()
        if content:
            normalized.append({"heading": heading, "content": content})
    return normalized


def _normalize_tables(tables: list[dict] | None) -> list[dict]:
    normalized = []
    for table in tables or []:
        if not isinstance(table, dict):
            continue
        title = str(table.get("title") or "").strip() or None
        columns = table.get("columns") or []
        rows = table.get("rows") or []
        if not isinstance(columns, list):
            columns = []
        if not isinstance(rows, list):
            rows = []
        normalized.append({
            "title": title,
            "columns": [str(col) for col in columns if str(col).strip()],
            "rows": rows,
        })
    return normalized


def to_canonical_document(
    url: str,
    title: str,
    text: str,
    strategy: str,
    evidence_ids: list[int],
    extra_metadata: dict | None = None,
    sections: list[dict] | None = None,
    tables: list[dict] | None = None,
) -> dict:
    normalized_sections = _normalize_sections(sections, text)
    normalized_tables = _normalize_tables(tables)
    metadata = {
        "extracted_ts": datetime.now(timezone.utc).isoformat(),
        "evidence_ids": evidence_ids,
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    payload = {
        "title": title or "Untitled",
        "url": url,
        "strategy": strategy,
        "sections": normalized_sections,
        "tables": normalized_tables,
        "metadata": metadata,
    }
    return payload


def _compute_quality_metrics(doc_payload: dict) -> dict:
    sections = [s.get("content", "").strip() for s in doc_payload.get("sections", []) if s.get("content")]
    total_chars = sum(len(section) for section in sections)
    section_count = len(sections)
    avg_section_chars = (total_chars / section_count) if section_count else 0.0
    long_sections = sum(1 for section in sections if len(section) >= 80)
    long_section_ratio = (long_sections / section_count) if section_count else 0.0
    table_count = len(doc_payload.get("tables", []))

    words = re.findall(r"\w+", " ".join(sections).lower())
    unique_words = len(set(words))
    lexical_diversity = (unique_words / len(words)) if words else 0.0

    coverage_score = min(total_chars / 2000.0, 1.0)
    structure_score = min(section_count / 8.0, 1.0)
    density_score = min(avg_section_chars / 350.0, 1.0)
    lexical_score = min(lexical_diversity / 0.7, 1.0)
    completeness_score = min(long_section_ratio / 0.75, 1.0)
    table_score = min(table_count / 3.0, 1.0)

    quality_score = round(
        (
            coverage_score * 0.32
            + structure_score * 0.14
            + density_score * 0.19
            + lexical_score * 0.15
            + completeness_score * 0.15
            + table_score * 0.05
        ),
        4,
    )

    return {
        "quality_score": quality_score,
        "text_length_chars": total_chars,
        "section_count": section_count,
        "table_count": table_count,
        "avg_section_chars": round(avg_section_chars, 2),
        "long_section_ratio": round(long_section_ratio, 4),
        "lexical_diversity": round(lexical_diversity, 4),
    }


def persist_canonical_document(base_dir: str, doc_payload: dict) -> tuple[str, float]:
    return persist_canonical_document_for_key(base_dir=base_dir, doc_payload=doc_payload, document_key=doc_payload["url"])


def persist_canonical_document_for_key(base_dir: str, doc_payload: dict, document_key: str) -> tuple[str, float]:
    metrics = _compute_quality_metrics(doc_payload)
    doc_payload.setdefault("metadata", {})["quality_metrics"] = metrics

    url_hash = hashlib.sha256(document_key.encode("utf-8")).hexdigest()[:12]
    path = Path(base_dir) / f"canonical_{url_hash}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path), float(metrics["quality_score"])
