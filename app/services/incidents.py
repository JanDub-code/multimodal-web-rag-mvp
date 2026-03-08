import json
import logging

from sqlalchemy.orm import Session

from app.db.models import Incident

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


def log_captcha_incident(db: Session, source_id: int, url: str, evidence_refs: list[int], reason: str) -> Incident:
    incident = Incident(
        type="captcha",
        source_id=source_id,
        url=url,
        severity="high",
        status="open",
        evidence_refs=json.dumps({"evidence_ids": evidence_refs, "reason": reason}),
    )
    db.add(incident)
    db.flush()
    logger.info("CAPTCHA incident logged for %s (reason: %s)", url, reason)
    return incident
