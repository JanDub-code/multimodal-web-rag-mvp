import json
import logging

from sqlalchemy.orm import Session

from app.db.models import AuditLog

logger = logging.getLogger(__name__)


def write_audit(db: Session, action: str, object_ref: str, user_id: int | None = None, metadata: dict | None = None) -> None:
    entry = AuditLog(
        user_id=user_id,
        action=action,
        object_ref=object_ref,
        metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
    )
    db.add(entry)
    db.flush()
    logger.debug("Audit: %s on %s by user %s", action, object_ref, user_id)
