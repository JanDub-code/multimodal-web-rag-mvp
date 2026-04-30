import json
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.routes_auth import require_roles
from app.db.models import AuditLog, User
from app.db.session import get_db

router = APIRouter(prefix="/api/audit", tags=["audit"])

# Mapování interních action názvů na event_type zobrazený ve frontendu
_ACTION_TO_EVENT_TYPE: dict[str, str] = {
    "query.executed": "QUERY",
    "ingest.run": "INGEST",
    "ingest.completed": "INGEST",
    "auth.login": "LOGIN",
    "compliance.confirmed": "COMPLIANCE CONFIRM",
    "compliance.bypassed": "COMPLIANCE CONFIRM",
    "model.call": "TEST RUN",
    "incident.captcha": "CAPTCHA ERROR",
    "settings.updated": "SETTINGS UPDATE",
}


def _map_event_type(action: str) -> str:
    """Vrátí event_type pro frontend; neznámé akce vrátí action uppercase."""
    return _ACTION_TO_EVENT_TYPE.get(action, action.upper())


def _build_detail(action: str, metadata_json: str | None, object_ref: str) -> str:
    """Sestaví čitelný detail z metadata_json a object_ref."""
    if not metadata_json:
        return object_ref
    try:
        meta = json.loads(metadata_json)
    except (ValueError, TypeError):
        return object_ref

    parts: list[str] = []

    if action.startswith("query"):
        if q := meta.get("query"):
            parts.append(f'"{q[:120]}"')
        if mode := meta.get("mode"):
            parts.append(f"mode={mode}")
    elif action.startswith("ingest"):
        if url := meta.get("url"):
            parts.append(url)
        if strategy := meta.get("strategy"):
            parts.append(f"strategy={strategy}")
        if status := meta.get("status"):
            parts.append(f"status={status}")
    elif "compliance" in action:
        if reason := meta.get("compliance_reason"):
            parts.append(reason)
        bypassed = meta.get("compliance_bypassed")
        if bypassed is True:
            parts.append("bypassed")
    elif action == "auth.login":
        parts.append(object_ref)

    return ", ".join(parts) if parts else object_ref


@router.get("/")
def get_audit_logs(
    date_from: date | None = Query(default=None, alias="dateFrom"),
    date_to: date | None = Query(default=None, alias="dateTo"),
    role: str | None = Query(default=None),
    event_type: str | None = Query(default=None, alias="type"),
    limit: int = Query(default=200, ge=1, le=1000),
    _user: User = Depends(require_roles("Admin", "Curator")),
    db: Session = Depends(get_db),
):
    query = (
        db.query(AuditLog, User)
        .outerjoin(User, AuditLog.user_id == User.id)
        .order_by(AuditLog.ts.desc())
    )

    if date_from:
        query = query.filter(AuditLog.ts >= date_from)
    if date_to:
        from datetime import timedelta
        query = query.filter(AuditLog.ts < date_to + timedelta(days=1))

    rows = query.limit(limit).all()

    result = []
    for log, user in rows:
        mapped_event = _map_event_type(log.action)

        # Filtr event_type (po mapování)
        if event_type and event_type.upper() not in ("VŠE", "ALL") and mapped_event != event_type.upper():
            continue

        actor_role = user.role.upper() if user else "SYSTEM"

        # Filtr role
        if role and role.upper() not in ("VŠICHNI", "ALL") and actor_role != role.upper():
            continue

        result.append({
            "id": log.id,
            "ts": log.ts.isoformat(),
            "actor": user.username if user else "system",
            "role": actor_role,
            "event_type": mapped_event,
            "detail": _build_detail(log.action, log.metadata_json, log.object_ref),
        })

    return result
