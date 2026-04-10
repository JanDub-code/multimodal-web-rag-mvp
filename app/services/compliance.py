import json
from dataclasses import dataclass
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import AuditLog, User
from app.services.audit import write_audit


settings = get_settings()
_enforcement_override: bool | None = None


@dataclass
class ComplianceDecision:
    operation_id: str
    compliance_confirmed: bool
    compliance_bypassed: bool
    compliance_reason: str
    enforcement_enabled: bool


def generate_operation_id() -> str:
    return f"op-{uuid4()}"


def set_compliance_enforcement_override(value: bool | None) -> None:
    global _enforcement_override
    _enforcement_override = value


def get_compliance_enforcement() -> bool:
    if _enforcement_override is None:
        return settings.compliance_enforcement
    return _enforcement_override


def get_compliance_mode_source() -> str:
    if _enforcement_override is None:
        return "env"
    return "runtime_override"


def resolve_sensitive_action_compliance(
    *,
    db: Session,
    user: User,
    action_type: str,
    operation_id: str | None = None,
    compliance_confirmed: bool | None = None,
    compliance_reason: str | None = None,
    compliance_bypassed: bool | None = None,
) -> ComplianceDecision:
    resolved_operation_id = (operation_id or "").strip() or generate_operation_id()
    confirmed = bool(compliance_confirmed)
    reason = (compliance_reason or "").strip()
    enforcement_enabled = get_compliance_enforcement()

    if enforcement_enabled and not confirmed:
        raise HTTPException(
            status_code=422,
            detail="Compliance confirmation is required when COMPLIANCE_ENFORCEMENT=true.",
        )

    bypassed = False
    if not confirmed:
        bypassed = True if compliance_bypassed is None else bool(compliance_bypassed)
    elif compliance_bypassed:
        bypassed = False

    write_audit(
        db,
        action="compliance.bypassed" if bypassed else "compliance.confirmed",
        object_ref=f"action:{action_type}",
        user_id=user.id,
        metadata={
            "action_type": action_type,
            "operation_id": resolved_operation_id,
            "reason": reason,
            "confirmed": confirmed,
            "compliance_bypassed": bypassed,
            "compliance_enforcement": enforcement_enabled,
        },
    )

    return ComplianceDecision(
        operation_id=resolved_operation_id,
        compliance_confirmed=confirmed,
        compliance_bypassed=bypassed,
        compliance_reason=reason,
        enforcement_enabled=enforcement_enabled,
    )


def parse_metadata_json(metadata_json: str | None) -> dict:
    if not metadata_json:
        return {}
    try:
        parsed = json.loads(metadata_json)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def audit_log_to_compliance_entry(entry: AuditLog, username: str | None) -> dict:
    payload = parse_metadata_json(entry.metadata_json)
    if username:
        resolved_user = username
    elif entry.user_id is not None:
        resolved_user = f"user:{entry.user_id}"
    else:
        resolved_user = "unknown"
    return {
        "id": entry.id,
        "timestamp": entry.ts.isoformat(),
        "user": resolved_user,
        "action": payload.get("action_type") or payload.get("action") or "unknown",
        "operation_id": payload.get("operation_id"),
        "reason": payload.get("reason") or "",
        "confirmed": bool(payload.get("confirmed")),
        "compliance_bypassed": bool(payload.get("compliance_bypassed")),
        "request_id": payload.get("request_id"),
    }
