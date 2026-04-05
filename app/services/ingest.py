import asyncio
import hashlib
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytesseract
from bs4 import BeautifulSoup
from PIL import Image, ImageOps
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Chunk, Document, Embedding, Evidence, IngestJob, Source
from app.services.chunking import chunk_sections
from app.services.extract import persist_canonical_document_for_key, to_canonical_document
from app.services.incidents import detect_captcha_heuristic, log_captcha_incident, log_ingest_incident
from app.services.multimodal import extract_structured_document_from_image, llm_chat_generate
from app.services.retrieval import delete_vectors_by_chunk_ids, upsert_chunk_vectors
from app.services.url_safety import SafeSession, UnsafeUrlError, validate_public_url

logger = logging.getLogger(__name__)
settings = get_settings()

_SAFE_SESSION = SafeSession(max_redirects=5)
_SAFE_HEADERS = {"User-Agent": "Local-MVP-Bot/1.0"}


def _sha256_file(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _store_text_evidence(db: Session, kind: str, folder: str, content: str) -> Evidence:
    filename = f"{kind}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}.txt"
    out_path = Path(folder) / filename
    out_path.write_text(content, encoding="utf-8")
    evidence = Evidence(type=kind, storage_uri=str(out_path), hash=_sha256_text(content))
    db.add(evidence)
    db.flush()
    return evidence


def _store_screenshot_evidence(db: Session, screenshot_path: Path) -> Evidence:
    evidence = Evidence(type="screenshot", storage_uri=str(screenshot_path), hash=_sha256_file(screenshot_path))
    db.add(evidence)
    db.flush()
    return evidence


def _normalize_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _html_fetch(url: str) -> tuple[str, str]:
    response = _SAFE_SESSION.get(url, timeout=20, headers=_SAFE_HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")
    title = (soup.title.text or "").strip() if soup.title else ""
    for script in soup(["script", "style", "noscript"]):
        script.extract()
    text = "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())
    return title, text


async def _playwright_route_guard(route, request) -> None:
    try:
        validate_public_url(request.url)
    except UnsafeUrlError:
        logger.warning("Blocked non-public Playwright request: %s", request.url)
        await route.abort(error_code="blockedbyclient")
    else:
        await route.continue_()


def _run_playwright_in_fresh_loop(url: str, screenshot_path: str) -> tuple[str, str]:
    """Run Playwright in a fresh ProactorEventLoop (required on Windows inside uvicorn threads)."""

    async def _pw_async():
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1440, "height": 2200})
            await page.route("**/*", _playwright_route_guard)
            await page.goto(url, wait_until="networkidle", timeout=45000)
            title = await page.title()
            dom_text = await page.inner_text("body")
            await page.screenshot(path=screenshot_path, full_page=True)
            await browser.close()
        return title or "", dom_text or ""

    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_pw_async())
    finally:
        loop.close()


def _extract_screenshot_text(screenshot_path: str) -> str:
    def _vision_ocr_fallback() -> str:
        model = settings.llm_vision_model or settings.llm_model
        if not model:
            return ""
        prompt = (
            "Extract all readable text from this webpage screenshot. "
            "Return plain text only in natural reading order. "
            "Do not summarize and do not add commentary."
        )
        text = llm_chat_generate(
            prompt=prompt,
            model=model,
            image_paths=[screenshot_path],
            timeout=max(60, settings.vision_timeout_seconds),
        )
        return _normalize_text(text or "")

    try:
        with Image.open(screenshot_path) as image:
            grayscale = ImageOps.grayscale(image)
            boosted = ImageOps.autocontrast(grayscale)
            text = pytesseract.image_to_string(boosted, lang="eng")
        return _normalize_text(text)
    except pytesseract.TesseractNotFoundError:
        logger.warning("Tesseract is not installed; falling back to vision OCR for %s", screenshot_path)
        return _vision_ocr_fallback()
    except Exception:
        logger.warning("OCR extraction failed for screenshot %s", screenshot_path, exc_info=True)
        return _vision_ocr_fallback()


def _render_and_screenshot(url: str) -> tuple[str, str, str, str]:
    screenshot_name = f"shot_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}.png"
    screenshot_path = Path(settings.screenshot_dir) / screenshot_name

    title, dom_text = _run_playwright_in_fresh_loop(url, str(screenshot_path))
    ocr_text = _extract_screenshot_text(str(screenshot_path))

    return title, dom_text, str(screenshot_path), ocr_text


def _is_text_weak(text: str) -> bool:
    return len((text or "").strip()) < settings.quality_threshold_chars


def _merge_text_sources(dom_text: str, ocr_text: str) -> str:
    dom_text = _normalize_text(dom_text)
    ocr_text = _normalize_text(ocr_text)

    if not dom_text:
        return ocr_text
    if not ocr_text:
        return dom_text
    if ocr_text in dom_text:
        return dom_text
    if dom_text in ocr_text:
        return ocr_text
    return f"{dom_text}\n\n[OCR]\n{ocr_text}"


def _cleanup_old_document(db: Session, source_id: int, url: str) -> None:
    def _remove_canonical_file_if_unreferenced(document: Document) -> None:
        storage_uri = (document.content_structured_uri or "").strip()
        if not storage_uri:
            return
        still_referenced = (
            db.query(Document)
            .filter(Document.id != document.id, Document.content_structured_uri == storage_uri)
            .count()
        )
        if still_referenced:
            return
        path = Path(storage_uri)
        if path.exists() and path.is_file():
            try:
                path.unlink()
            except OSError:
                logger.warning("Failed to remove canonical file %s", storage_uri, exc_info=True)

    existing_docs = db.query(Document).filter(Document.source_id == source_id, Document.url == url).all()
    if not existing_docs:
        return

    for doc in existing_docs:
        chunk_ids = [c.id for c in db.query(Chunk).filter(Chunk.doc_id == doc.id).all()]
        if chunk_ids:
            db.query(Embedding).filter(Embedding.chunk_id.in_(chunk_ids)).delete(synchronize_session=False)
            db.query(Chunk).filter(Chunk.doc_id == doc.id).delete(synchronize_session=False)
            delete_vectors_by_chunk_ids(chunk_ids)
        _remove_canonical_file_if_unreferenced(doc)
        db.delete(doc)

    db.flush()
    logger.info("Cleaned up %d old document(s) for source %d, URL %s", len(existing_docs), source_id, url)


def _load_evidence_items(db: Session, evidence_ids: list[int]) -> list[dict]:
    if not evidence_ids:
        return []
    rows = db.query(Evidence).filter(Evidence.id.in_(evidence_ids)).all()
    by_id = {row.id: row for row in rows}
    items: list[dict] = []
    for evidence_id in evidence_ids:
        row = by_id.get(evidence_id)
        if not row:
            continue
        items.append(
            {
                "id": row.id,
                "type": row.type,
                "storage_uri": row.storage_uri,
                "hash": row.hash,
            }
        )
    return items


def _table_to_text(table: dict) -> str:
    title = str(table.get("title") or "Table").strip()
    columns = table.get("columns") or []
    rows = table.get("rows") or []

    lines: list[str] = [title] if title else []
    if columns:
        lines.append(" | ".join(str(col) for col in columns))
    for row in rows[:20]:
        if isinstance(row, dict):
            if columns:
                ordered = [str(row.get(col, "")) for col in columns]
            else:
                ordered = [f"{key}: {value}" for key, value in row.items()]
            lines.append(" | ".join(value for value in ordered if value))
        elif isinstance(row, list):
            lines.append(" | ".join(str(value) for value in row))
        else:
            lines.append(str(row))
    return "\n".join(line for line in lines if str(line).strip()).strip()


def _build_chunk_rows(canonical: dict) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = [("text", chunk) for chunk in chunk_sections(canonical.get("sections", [])) if chunk.strip()]
    for table in canonical.get("tables", []):
        table_text = _table_to_text(table)
        if table_text:
            rows.append(("table", table_text))
    return rows


def _classify_ingest_failure(exc: Exception) -> str:
    if isinstance(exc, UnsafeUrlError):
        return "policy_error"
    lowered = str(exc).lower()
    if any(keyword in lowered for keyword in ("playwright", "screenshot", "browser", "networkidle")):
        return "render_error"
    if any(keyword in lowered for keyword in ("json", "parse", "decode", "malformed")):
        return "parse_error"
    if any(keyword in lowered for keyword in ("timeout", "connection", "dns", "http", "fetch")):
        return "fetch_error"
    return "ingest_failure"


def run_ingest(db: Session, source_id: int, url: str) -> dict:
    source = db.get(Source, source_id)
    if not source:
        raise ValueError("Source not found")

    validate_public_url(url)

    job = IngestJob(source_id=source_id, url=url, strategy="HTML", status="running")
    db.add(job)
    db.flush()

    strategy = "HTML"
    title = ""
    text = ""
    evidence_ids: list[int] = []
    ocr_used = False
    ocr_chars = 0
    vision_used = False
    vision_model: str | None = None
    vision_summary: str | None = None
    vision_sections: list[dict] | None = None
    vision_tables: list[dict] | None = None

    try:
        screenshot_path: str | None = None
        dom_text = ""
        ocr_text = ""
        try:
            title, text = _html_fetch(url)
            html_evidence = _store_text_evidence(db, "html", settings.dom_snapshot_dir, text)
            evidence_ids.append(html_evidence.id)

            if _is_text_weak(text):
                strategy = "RENDERED_DOM"
                title, dom_text, screenshot_path, ocr_text = _render_and_screenshot(url)
                text = _merge_text_sources(dom_text, ocr_text)
                dom_evidence = _store_text_evidence(db, "dom", settings.dom_snapshot_dir, dom_text)
                shot_evidence = _store_screenshot_evidence(db, Path(screenshot_path))
                evidence_ids.extend([dom_evidence.id, shot_evidence.id])
                if ocr_text:
                    ocr_evidence = _store_text_evidence(db, "ocr", settings.dom_snapshot_dir, ocr_text)
                    evidence_ids.append(ocr_evidence.id)
                    ocr_used = True
                    ocr_chars = len(ocr_text)
        except Exception as exc:
            logger.warning("HTML fetch failed for %s, falling back to SCREENSHOT", url, exc_info=True)
            try:
                log_ingest_incident(
                    db,
                    incident_type="fetch_error",
                    source_id=source_id,
                    url=url,
                    evidence_refs=evidence_ids,
                    reason=str(exc),
                    severity="low",
                    status="observed",
                    metadata={"stage": "html_fetch", "fallback": "screenshot"},
                )
            except Exception:
                logger.exception("Failed to log fetch_error incident before fallback")
            strategy = "SCREENSHOT"
            title, dom_text, screenshot_path, ocr_text = _render_and_screenshot(url)
            text = _merge_text_sources(dom_text, ocr_text)
            dom_evidence = _store_text_evidence(db, "dom", settings.dom_snapshot_dir, dom_text)
            shot_evidence = _store_screenshot_evidence(db, Path(screenshot_path))
            evidence_ids.extend([dom_evidence.id, shot_evidence.id])
            if ocr_text:
                ocr_evidence = _store_text_evidence(db, "ocr", settings.dom_snapshot_dir, ocr_text)
                evidence_ids.append(ocr_evidence.id)
                ocr_used = True
                ocr_chars = len(ocr_text)

        if screenshot_path:
            structured_doc, raw_vision_output = extract_structured_document_from_image(
                image_path=screenshot_path,
                url=url,
                title_hint=title,
                dom_text=dom_text,
                ocr_text=ocr_text,
            )
            if raw_vision_output:
                vision_evidence = _store_text_evidence(db, "vision", settings.dom_snapshot_dir, raw_vision_output)
                evidence_ids.append(vision_evidence.id)
            if structured_doc:
                vision_used = True
                vision_model = structured_doc.get("model")
                vision_summary = structured_doc.get("visual_summary")
                vision_sections = structured_doc.get("sections")
                vision_tables = structured_doc.get("tables")
                if structured_doc.get("title"):
                    title = structured_doc["title"]
                if vision_sections:
                    text = "\n\n".join(section.get("content", "") for section in vision_sections if section.get("content"))

        is_captcha, reason = detect_captcha_heuristic(text, url)
        incident_id = None
        if is_captcha:
            incident = log_captcha_incident(db, source_id=source_id, url=url, evidence_refs=evidence_ids, reason=reason)
            incident_id = incident.id
            _cleanup_old_document(db, source_id, url)
            job.strategy = strategy
            job.status = "blocked_captcha"
            job.finished_ts = datetime.now(timezone.utc)
            db.commit()
            logger.info("Ingest blocked by CAPTCHA: job=%d strategy=%s url=%s", job.id, strategy, url)
            return {
                "job_id": job.id,
                "strategy": strategy,
                "status": "blocked_captcha",
                "message": "CAPTCHA or bot challenge detected. Evidence was stored, but the page was not indexed.",
                "document_id": None,
                "evidence_ids": evidence_ids,
                "incident_id": incident_id,
            }

        _cleanup_old_document(db, source_id, url)

        canonical = to_canonical_document(
            url=url,
            title=title,
            text=text,
            strategy=strategy,
            evidence_ids=evidence_ids,
            extra_metadata={
                "ocr_used": ocr_used,
                "ocr_chars": ocr_chars,
                "vision_used": vision_used,
                "vision_model": vision_model,
                "vision_summary": vision_summary,
            },
            sections=vision_sections,
            tables=vision_tables,
        )
        canonical_uri, quality_score = persist_canonical_document_for_key(
            base_dir=settings.evidence_dir,
            doc_payload=canonical,
            document_key=f"{source_id}:{url}",
        )

        document = Document(
            source_id=source_id,
            url=url,
            doc_version=1,
            content_structured_uri=canonical_uri,
            quality_score=quality_score,
        )
        db.add(document)
        db.flush()

        evidence_items = _load_evidence_items(db, evidence_ids)
        chunk_rows = _build_chunk_rows(canonical)
        qdrant_rows = []
        for chunk_type, chunk_text in chunk_rows:
            citations = {
                "url": url,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "evidence_ids": evidence_ids,
                "evidence_items": evidence_items,
            }
            chunk = Chunk(doc_id=document.id, chunk_type=chunk_type, text=chunk_text, citations_ref=json.dumps(citations))
            db.add(chunk)
            db.flush()

            embedding = Embedding(chunk_id=chunk.id, model_id=settings.embedding_model, vector_ref=f"qdrant:{chunk.id}")
            db.add(embedding)
            qdrant_rows.append(
                {
                    "chunk_id": chunk.id,
                    "doc_id": document.id,
                    "source_id": source_id,
                    "url": url,
                    "text": chunk_text,
                    "chunk_type": chunk_type,
                    "citations_ref": json.dumps(citations),
                }
            )

        upsert_chunk_vectors(qdrant_rows)

        job.strategy = strategy
        job.status = "completed"
        job.finished_ts = datetime.now(timezone.utc)
        db.commit()

        logger.info("Ingest completed: job=%d strategy=%s doc=%d chunks=%d", job.id, strategy, document.id, len(chunk_rows))
        return {
            "job_id": job.id,
            "strategy": strategy,
            "status": "completed",
            "document_id": document.id,
            "evidence_ids": evidence_ids,
            "incident_id": incident_id,
        }

    except Exception as exc:
        logger.exception("Ingest failed for source %d, URL %s", source_id, url)
        db.rollback()
        incident_type = _classify_ingest_failure(exc)
        failure_incident_id = None
        try:
            failure_incident = log_ingest_incident(
                db,
                incident_type=incident_type,
                source_id=source_id,
                url=url,
                evidence_refs=[],
                reason=str(exc),
                severity="high",
                status="open",
                metadata={"stage": "run_ingest", "strategy": strategy},
            )
            failure_incident_id = failure_incident.id
        except Exception:
            logger.exception("Failed to log ingest failure incident")
        job.status = "failed"
        job.error_code = incident_type
        job.finished_ts = datetime.now(timezone.utc)
        db.add(job)
        try:
            db.commit()
            logger.info(
                "Ingest marked as failed: job=%s incident_type=%s incident_id=%s",
                job.id,
                incident_type,
                failure_incident_id,
            )
        except Exception:
            logger.exception("Failed to update job status to 'failed'")
        raise

