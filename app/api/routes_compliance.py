from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.routes_auth import require_roles
from app.db.models import AuditLog, User
from app.db.session import get_db
from app.services.compliance import (
    audit_log_to_compliance_entry,
    get_compliance_enforcement,
    get_compliance_mode_source,
    resolve_sensitive_action_compliance,
    set_compliance_enforcement_override,
)


router = APIRouter(prefix="/api/compliance", tags=["compliance"])


class ComplianceConfirmRequest(BaseModel):
    action: str = Field(..., min_length=3, max_length=120)
    operation_id: str | None = Field(default=None, max_length=160)
    reason: str | None = Field(default=None, max_length=500)
    confirmed: bool = True
    compliance_bypassed: bool | None = None


class ComplianceModeUpdateRequest(BaseModel):
    enforcement: bool


@router.get("/mode")
def get_mode(
    user: User = Depends(require_roles("Admin", "Curator", "Analyst", "User")),
):
    return {
        "enforcement": get_compliance_enforcement(),
        "source": get_compliance_mode_source(),
    }


@router.put("/mode")
def set_mode(
    payload: ComplianceModeUpdateRequest,
    user: User = Depends(require_roles("Admin")),
):
    set_compliance_enforcement_override(payload.enforcement)
    return {
        "enforcement": get_compliance_enforcement(),
        "source": get_compliance_mode_source(),
    }


@router.post("/confirm")
def confirm(
    payload: ComplianceConfirmRequest,
    user: User = Depends(require_roles("Admin", "Curator", "Analyst", "User")),
    db: Session = Depends(get_db),
):
    decision = resolve_sensitive_action_compliance(
        db=db,
        user=user,
        action_type=payload.action,
        operation_id=payload.operation_id,
        compliance_confirmed=payload.confirmed,
        compliance_reason=payload.reason,
        compliance_bypassed=payload.compliance_bypassed,
    )
    db.commit()
    return {
        "status": "ok",
        "enforcement": decision.enforcement_enabled,
        "operation_id": decision.operation_id,
        "action": payload.action,
        "reason": decision.compliance_reason,
        "confirmed": decision.compliance_confirmed,
        "compliance_bypassed": decision.compliance_bypassed,
    }


@router.get("/history")
def history(
    limit: int = Query(default=100, ge=1, le=500),
    user: User = Depends(require_roles("Admin", "Curator", "Analyst", "User")),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(AuditLog, User.username)
        .outerjoin(User, User.id == AuditLog.user_id)
        .filter(AuditLog.action.in_(("compliance.confirmed", "compliance.bypassed")))
        .order_by(AuditLog.id.desc())
        .limit(limit)
        .all()
    )
    return [audit_log_to_compliance_entry(entry, username) for entry, username in rows]
