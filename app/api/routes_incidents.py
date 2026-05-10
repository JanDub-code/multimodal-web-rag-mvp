import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.routes_auth import require_roles
from app.db.models import Incident, Source, User
from app.db.session import get_db
from app.services.audit import write_audit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


class IncidentCreate(BaseModel):
    source_id: int
    url: str = Field(..., min_length=1, max_length=1000)
    type: str = Field(default="captcha", max_length=50)
    severity: str = Field(default="medium", max_length=20)


class IncidentResolve(BaseModel):
    resolution_note: str | None = Field(default=None, max_length=1000)


@router.post("/", status_code=201)
def create_incident(
    payload: IncidentCreate,
    user: User = Depends(require_roles("Admin", "Curator")),
    db: Session = Depends(get_db),
):
    source = db.get(Source, payload.source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    incident = Incident(
        type=payload.type,
        source_id=payload.source_id,
        url=payload.url,
        severity=payload.severity,
        status="open",
        evidence_refs="",
    )
    db.add(incident)
    db.flush()
    write_audit(db, action="incident.created", object_ref=f"incident:{incident.id}", user_id=user.id)
    db.commit()
    return {
        "id": incident.id,
        "type": incident.type,
        "source_id": incident.source_id,
        "source_name": source.name,
        "url": incident.url,
        "severity": incident.severity,
        "status": incident.status,
        "created_ts": incident.created_ts.isoformat() if incident.created_ts else None,
    }


@router.get("/")
def list_incidents(
    status: str | None = None,
    user: User = Depends(require_roles("Admin", "Curator", "Analyst")),
    db: Session = Depends(get_db),
):
    q = db.query(Incident)
    if status:
        q = q.filter(Incident.status == status)
    rows = q.order_by(Incident.created_ts.desc()).all()

    source_ids = {r.source_id for r in rows}
    sources = {s.id: s for s in db.query(Source).filter(Source.id.in_(source_ids)).all()} if source_ids else {}

    return [
        {
            "id": r.id,
            "type": r.type,
            "source_id": r.source_id,
            "source_name": sources.get(r.source_id, None) and sources[r.source_id].name,
            "url": r.url,
            "severity": r.severity,
            "status": r.status,
            "created_ts": r.created_ts.isoformat() if r.created_ts else None,
            "resolved_ts": r.resolved_ts.isoformat() if r.resolved_ts else None,
            "resolution_note": r.resolution_note,
        }
        for r in rows
    ]


@router.get("/{incident_id}")
def get_incident(
    incident_id: int,
    user: User = Depends(require_roles("Admin", "Curator", "Analyst")),
    db: Session = Depends(get_db),
):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    source = db.get(Source, incident.source_id)
    return {
        "id": incident.id,
        "type": incident.type,
        "source_id": incident.source_id,
        "source_name": source.name if source else None,
        "url": incident.url,
        "severity": incident.severity,
        "status": incident.status,
        "created_ts": incident.created_ts.isoformat() if incident.created_ts else None,
        "resolved_ts": incident.resolved_ts.isoformat() if incident.resolved_ts else None,
        "resolution_note": incident.resolution_note,
        "evidence_refs": incident.evidence_refs,
    }


@router.put("/{incident_id}/resolve", status_code=200)
def resolve_incident(
    incident_id: int,
    payload: IncidentResolve,
    user: User = Depends(require_roles("Admin", "Curator")),
    db: Session = Depends(get_db),
):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if incident.status == "resolved":
        raise HTTPException(status_code=409, detail="Incident is already resolved")

    incident.status = "resolved"
    incident.resolved_ts = datetime.now(timezone.utc)
    incident.resolution_note = payload.resolution_note or ""

    write_audit(db, action="incident.resolved", object_ref=f"incident:{incident_id}", user_id=user.id)
    db.commit()
    return {"status": "resolved", "incident_id": incident_id}


@router.delete("/{incident_id}", status_code=204)
def delete_incident(
    incident_id: int,
    user: User = Depends(require_roles("Admin")),
    db: Session = Depends(get_db),
):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    write_audit(db, action="incident.deleted", object_ref=f"incident:{incident_id}", user_id=user.id)
    db.delete(incident)
    db.commit()
    return None
