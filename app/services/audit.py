import json
import logging

from sqlalchemy.orm import Session

from app.db.models import AuditLog
from app.services.request_context import get_request_id

logger = logging.getLogger(__name__)


def write_audit(db: Session, action: str, object_ref: str, user_id: int | None = None, metadata: dict | None = None) -> None:
    payload = dict(metadata or {})
    request_id = get_request_id()
    if request_id and "request_id" not in payload:
        payload["request_id"] = request_id
    entry = AuditLog(
        user_id=user_id,
        action=action,
        object_ref=object_ref,
        metadata_json=json.dumps(payload, ensure_ascii=False),
    )
    db.add(entry)
    db.flush()
    logger.debug("Audit: action=%s object=%s user=%s request_id=%s", action, object_ref, user_id, payload.get("request_id"))
