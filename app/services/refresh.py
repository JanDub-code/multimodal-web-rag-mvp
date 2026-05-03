from __future__ import annotations

import asyncio
import logging
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import nullsfirst
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import IngestJob, SourceUrl
from app.db.session import SessionLocal
from app.services.audit import write_audit
from app.services.ingest import run_ingest
from app.services.request_context import get_request_id, reset_request_id, set_request_id
from app.services.source_urls import (
    effective_refresh_interval_minutes,
    ensure_source_url,
    is_stale,
    mark_attempt,
    recent_attempt_block,
)

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class RefreshOutcome:
    status: str
    job_id: int | None
    error: str | None


def _refresh_request_id() -> str:
    return f"refresh-{uuid4()}"


def _has_running_ingest(db: Session, source_id: int, url: str) -> bool:
    running = (
        db.query(IngestJob)
        .filter(
            IngestJob.source_id == source_id,
            IngestJob.url == url,
            IngestJob.status == "running",
        )
        .count()
    )
    return running > 0


def refresh_url(
    db: Session,
    *,
    source_id: int,
    url: str,
    refresh_interval_minutes: int | None = None,
    trigger: str = "manual",
) -> RefreshOutcome:
    source_url = ensure_source_url(
        db,
        source_id=source_id,
        url=url,
        refresh_interval_minutes=refresh_interval_minutes,
    )
    mark_attempt(source_url)

    if _has_running_ingest(db, source_id, url):
        logger.info("Refresh skipped for %s (running ingest)", url)
        return RefreshOutcome(status="skipped_running", job_id=None, error=None)

    try:
        result = run_ingest(
            db=db,
            source_id=source_id,
            url=url,
            refresh_interval_minutes=refresh_interval_minutes,
        )
        status = result.get("status", "unknown")
        return RefreshOutcome(status=status, job_id=result.get("job_id"), error=None)
    except Exception as exc:  # pragma: no cover - defensive path
        logger.exception("Refresh failed for %s", url)
        return RefreshOutcome(status="failed", job_id=None, error=str(exc))


def _collect_stale_urls(db: Session, limit: int) -> list[SourceUrl]:
    rows = (
        db.query(SourceUrl)
        .order_by(nullsfirst(SourceUrl.last_successful_ingest_ts), SourceUrl.id.asc())
        .all()
    )
    stale: list[SourceUrl] = []
    now = datetime.now(timezone.utc)
    for row in rows:
        if len(stale) >= limit:
            break
        if recent_attempt_block(row, now=now):
            continue
        if is_stale(row, now=now):
            stale.append(row)
    return stale


def refresh_stale_urls(db: Session, *, batch_size: int | None = None, trigger: str = "scheduler") -> dict:
    resolved_batch = batch_size or settings.refresh_scheduler_batch_size
    urls = _collect_stale_urls(db, limit=resolved_batch)
    total = len(urls)
    outcomes: list[RefreshOutcome] = []
    incident_types: list[str] = []
    url_summaries: list[dict] = []

    for row in urls:
        outcome = refresh_url(
            db,
            source_id=row.source_id,
            url=row.url,
            refresh_interval_minutes=row.refresh_interval_minutes,
            trigger=trigger,
        )
        outcomes.append(outcome)
        url_summaries.append(
            {
                "source_id": row.source_id,
                "url": row.url,
                "status": outcome.status,
                "job_id": outcome.job_id,
            }
        )
        if outcome.status in {"failed", "blocked_captcha"}:
            incident_types.append(outcome.status)

    status_counts = Counter(outcome.status for outcome in outcomes)
    summary = {
        "total": total,
        "status_counts": dict(status_counts),
        "incident_types": dict(Counter(incident_types)),
    }

    write_audit(
        db,
        action="refresh.batch",
        object_ref="refresh:stale_urls",
        metadata={
            "trigger": trigger,
            "batch_size": resolved_batch,
            "operation_id": get_request_id(),
            **summary,
            "urls": url_summaries,
        },
    )
    db.commit()
    return summary


async def refresh_scheduler_loop(stop_event: asyncio.Event | None = None) -> None:
    logger.info("Refresh scheduler started (interval=%ss)", settings.refresh_scheduler_interval_seconds)
    while True:
        if stop_event and stop_event.is_set():
            logger.info("Refresh scheduler stopped")
            return
        request_id = _refresh_request_id()
        token = set_request_id(request_id)
        try:
            with SessionLocal() as db:
                refresh_stale_urls(db, trigger="scheduler")
        except Exception:
            logger.exception("Refresh scheduler run failed")
        finally:
            reset_request_id(token)
        await asyncio.sleep(settings.refresh_scheduler_interval_seconds)
