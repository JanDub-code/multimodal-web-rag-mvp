import json
import logging

from sqlalchemy.orm import Session

from app.db.models import Incident
from app.services.request_context import get_request_id

logger = logging.getLogger(__name__)

CAPTCHA_MARKERS = [
    "captcha",
    "verify you are human",
    "are you human",
    "cloudflare",
    "robot check",
]


def detect_captcha_heuristic(text: str, url: str) -> tuple[bool, str]:
    lowered = (text or "").lower()
    for marker in CAPTCHA_MARKERS:
        if marker in lowered:
            return True, f"marker:{marker}"
    if "captcha" in url.lower():
        return True, "url_pattern"
    return False, ""


def log_ingest_incident(
    db: Session,
    *,
    incident_type: str,
    source_id: int,
    url: str,
    evidence_refs: list[int],
    reason: str,
    severity: str = "medium",
    status: str = "open",
    metadata: dict | None = None,
) -> Incident:
    payload = {"evidence_ids": evidence_refs, "reason": reason}
    incident_metadata = dict(metadata or {})
    request_id = get_request_id()
    if request_id and "request_id" not in incident_metadata:
        incident_metadata["request_id"] = request_id
    if incident_metadata:
        payload["metadata"] = incident_metadata
    incident = Incident(
        type=incident_type,
        source_id=source_id,
        url=url,
        severity=severity,
        status=status,
        evidence_refs=json.dumps(payload, ensure_ascii=False),
    )
    db.add(incident)
    db.flush()
    logger.info(
        "Ingest incident logged: type=%s severity=%s status=%s url=%s reason=%s",
        incident_type,
        severity,
        status,
        url,
        reason,
    )
    return incident


def log_captcha_incident(db: Session, source_id: int, url: str, evidence_refs: list[int], reason: str) -> Incident:
    return log_ingest_incident(
        db,
        incident_type="captcha",
        source_id=source_id,
        url=url,
        evidence_refs=evidence_refs,
        reason=reason,
        severity="high",
        status="open",
    )
