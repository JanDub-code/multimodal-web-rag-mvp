from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import SourceUrl

settings = get_settings()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def ensure_source_url(
    db: Session,
    *,
    source_id: int,
    url: str,
    refresh_interval_minutes: int | None = None,
) -> SourceUrl:
    row = (
        db.query(SourceUrl)
        .filter(SourceUrl.source_id == source_id, SourceUrl.url == url)
        .one_or_none()
    )
    if row:
        if refresh_interval_minutes is not None:
            row.refresh_interval_minutes = refresh_interval_minutes
        return row

    interval = refresh_interval_minutes or settings.refresh_default_interval_minutes
    row = SourceUrl(
        source_id=source_id,
        url=url,
        refresh_interval_minutes=interval,
    )
    db.add(row)
    db.flush()
    return row


def mark_attempt(row: SourceUrl, timestamp: datetime | None = None) -> None:
    row.last_attempt_ts = timestamp or datetime.now(timezone.utc)


def mark_success(row: SourceUrl, timestamp: datetime | None = None) -> None:
    row.last_successful_ingest_ts = timestamp or datetime.now(timezone.utc)


def effective_refresh_interval_minutes(row: SourceUrl) -> int:
    return int(row.refresh_interval_minutes or settings.refresh_default_interval_minutes)


def is_stale(row: SourceUrl, now: datetime | None = None) -> bool:
    reference = _as_utc(now or datetime.now(timezone.utc))
    interval = effective_refresh_interval_minutes(row)
    last_success = row.last_successful_ingest_ts
    if last_success is None:
        return True
    return reference - _as_utc(last_success) >= timedelta(minutes=interval)


def recent_attempt_block(row: SourceUrl, now: datetime | None = None) -> bool:
    if row.last_attempt_ts is None:
        return False
    reference = _as_utc(now or datetime.now(timezone.utc))
    return reference - _as_utc(row.last_attempt_ts) < timedelta(minutes=settings.refresh_retry_backoff_minutes)
