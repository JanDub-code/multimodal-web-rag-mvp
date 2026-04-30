from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes_auth import require_roles
from app.db.models import SystemSetting, User
from app.db.session import get_db
from app.services.audit import write_audit

router = APIRouter(prefix="/api/settings", tags=["settings"])

RETENTION_OPTIONS = ("30 dní", "60 dní", "90 dní", "1 rok")
DEFAULT_RETENTION = {
    "raw_evidence": "60 dní",
    "audit_logs": "60 dní",
    "vector_snapshot": "60 dní",
}
RETENTION_KEYS = {
    "raw_evidence": "retention.raw_evidence",
    "audit_logs": "retention.audit_logs",
    "vector_snapshot": "retention.vector_snapshot",
}


class RetentionSettings(BaseModel):
    raw_evidence: str = Field(default=DEFAULT_RETENTION["raw_evidence"])
    audit_logs: str = Field(default=DEFAULT_RETENTION["audit_logs"])
    vector_snapshot: str = Field(default=DEFAULT_RETENTION["vector_snapshot"])

    def model_post_init(self, __context) -> None:
        invalid = [
            value
            for value in (self.raw_evidence, self.audit_logs, self.vector_snapshot)
            if value not in RETENTION_OPTIONS
        ]
        if invalid:
            raise ValueError(f"Unsupported retention value: {', '.join(invalid)}")


class SettingsResponse(BaseModel):
    retention: RetentionSettings


class SettingsUpdateRequest(BaseModel):
    retention: RetentionSettings


def _setting_map(db: Session) -> dict[str, str]:
    rows = db.execute(select(SystemSetting).where(SystemSetting.key.in_(RETENTION_KEYS.values()))).scalars()
    return {row.key: row.value for row in rows}


def _read_retention(db: Session) -> RetentionSettings:
    values = _setting_map(db)
    return RetentionSettings(
        raw_evidence=values.get(RETENTION_KEYS["raw_evidence"], DEFAULT_RETENTION["raw_evidence"]),
        audit_logs=values.get(RETENTION_KEYS["audit_logs"], DEFAULT_RETENTION["audit_logs"]),
        vector_snapshot=values.get(RETENTION_KEYS["vector_snapshot"], DEFAULT_RETENTION["vector_snapshot"]),
    )


def _upsert_setting(db: Session, key: str, value: str) -> None:
    row = db.execute(select(SystemSetting).where(SystemSetting.key == key)).scalar_one_or_none()
    if row:
        row.value = value
        return
    db.add(SystemSetting(key=key, value=value))


@router.get("", response_model=SettingsResponse)
@router.get("/", response_model=SettingsResponse)
def get_settings(
    _user: User = Depends(require_roles("Admin")),
    db: Session = Depends(get_db),
):
    return SettingsResponse(retention=_read_retention(db))


@router.put("", response_model=SettingsResponse)
@router.put("/", response_model=SettingsResponse)
def update_settings(
    payload: SettingsUpdateRequest,
    user: User = Depends(require_roles("Admin")),
    db: Session = Depends(get_db),
):
    retention = payload.retention
    _upsert_setting(db, RETENTION_KEYS["raw_evidence"], retention.raw_evidence)
    _upsert_setting(db, RETENTION_KEYS["audit_logs"], retention.audit_logs)
    _upsert_setting(db, RETENTION_KEYS["vector_snapshot"], retention.vector_snapshot)
    write_audit(
        db,
        action="settings.updated",
        object_ref="system_settings:retention",
        user_id=user.id,
        metadata={"retention": retention.model_dump()},
    )
    db.commit()
    return SettingsResponse(retention=_read_retention(db))
