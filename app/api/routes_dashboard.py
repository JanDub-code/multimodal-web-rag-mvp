from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.routes_auth import require_roles
from app.db.models import AuditLog, Chunk, Document, Incident, IngestJob, Source, User
from app.db.session import get_db

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
def dashboard_stats(
    _user: User = Depends(require_roles("Admin", "Curator", "Analyst", "User")),
    db: Session = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    last_ingest_ts = db.query(func.max(IngestJob.finished_ts)).scalar()
    if last_ingest_ts is None:
        last_ingest_ts = db.query(func.max(IngestJob.started_ts)).scalar()

    return {
        "totalSources": db.query(Source).count(),
        "openIncidents": db.query(Incident).filter(Incident.status == "open").count(),
        "lastCrawl": last_ingest_ts.isoformat() if last_ingest_ts else None,
        "nextCrawl": None,
        "totalDocuments": db.query(Document).count(),
        "totalChunks": db.query(Chunk).count(),
        "queriesLast24h": (
            db.query(AuditLog)
            .filter(AuditLog.action == "query.executed", AuditLog.ts >= since)
            .count()
        ),
    }
