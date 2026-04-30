import logging
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.routes_auth import require_roles
from app.db.models import Document, Source, User
from app.db.session import get_db
from app.services.audit import write_audit
from app.services.compliance import resolve_sensitive_action_compliance
from app.services.ingest import run_ingest
from app.services.model_usage import ingest_model_usage
from app.services.refresh import refresh_url as run_refresh
from app.services.url_safety import UnsafeUrlError, validate_public_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


class SourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    base_url: str = Field(..., min_length=1, max_length=1000)
    permission_type: str = Field(default="public", min_length=1, max_length=100)
    permission_ref: str | None = Field(default=None, max_length=255)


class IngestRequest(BaseModel):
    source_id: int
    url: str = Field(..., min_length=1, max_length=2000)
    operation_id: str | None = Field(default=None, max_length=160)
    batch_id: str | None = Field(default=None, max_length=160)
    row_id: int | None = Field(default=None, ge=1)
    compliance_confirmed: bool | None = None
    compliance_reason: str | None = Field(default=None, max_length=500)
    compliance_bypassed: bool | None = None


class RefreshRequest(BaseModel):
    source_id: int
    url: str = Field(..., min_length=1, max_length=2000)
    operation_id: str | None = Field(default=None, max_length=160)
    batch_id: str | None = Field(default=None, max_length=160)
    row_id: int | None = Field(default=None, ge=1)
    refresh_interval_minutes: int | None = Field(default=None, ge=1)
    compliance_confirmed: bool | None = None
    compliance_reason: str | None = Field(default=None, max_length=500)
    compliance_bypassed: bool | None = None


def _validate_url_or_422(url: str) -> None:
    try:
        validate_public_url(url)
    except UnsafeUrlError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _effective_port(scheme: str, port: int | None) -> int | None:
    if port is not None:
        return port
    if scheme == "https":
        return 443
    if scheme == "http":
        return 80
    return None


def _normalize_origin(url: str) -> tuple[str, str, int | None]:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    return scheme, (parsed.hostname or "").lower(), _effective_port(scheme, parsed.port)


def _normalize_path_prefix(url: str) -> str:
    path = (urlparse(url).path or "/").rstrip("/")
    return path or "/"


def _validate_ingest_url_matches_source_or_422(source: Source, url: str) -> None:
    source_scheme, source_host, source_port = _normalize_origin(source.base_url)
    target_scheme, target_host, target_port = _normalize_origin(url)
    source_path = _normalize_path_prefix(source.base_url)
    target_path = _normalize_path_prefix(url)

    same_origin = (
        source_scheme == target_scheme
        and source_host == target_host
        and source_port == target_port
    )
    within_path = source_path == "/" or target_path == source_path or target_path.startswith(f"{source_path}/")
    if same_origin and within_path:
        return

    raise HTTPException(
        status_code=422,
        detail=f"URL '{url}' is outside the selected source scope '{source.base_url}'.",
    )


def _validate_permission_metadata_or_422(permission_type: str, permission_ref: str | None) -> tuple[str, str | None]:
    normalized_type = (permission_type or "").strip().lower()
    if not normalized_type:
        raise HTTPException(status_code=422, detail="Source permission_type is required.")

    normalized_ref = (permission_ref or "").strip() or None
    if normalized_type != "public" and not normalized_ref:
        raise HTTPException(
            status_code=422,
            detail="permission_ref is required when permission_type is not 'public'.",
        )
    return normalized_type, normalized_ref


def _validate_source_permission_or_422(source: Source) -> None:
    _validate_permission_metadata_or_422(source.permission_type, source.permission_ref)


@router.post("/sources")
def create_source(
    payload: SourceCreate,
    user: User = Depends(require_roles("Admin", "Curator")),
    db: Session = Depends(get_db),
):
    _validate_url_or_422(payload.base_url)
    permission_type, permission_ref = _validate_permission_metadata_or_422(
        payload.permission_type,
        payload.permission_ref,
    )

    source = Source(
        name=payload.name,
        base_url=payload.base_url,
        permission_type=permission_type,
        permission_ref=permission_ref,
    )
    db.add(source)
    db.flush()
    write_audit(db, action="source.create", object_ref=f"source:{source.id}", user_id=user.id)
    db.commit()
    return {"source_id": source.id, "name": source.name}


@router.get("/sources")
def list_sources(user: User = Depends(require_roles("Admin", "Curator", "Analyst", "User")), db: Session = Depends(get_db)):
    rows = db.query(Source).order_by(Source.id.desc()).all()
    return [{"id": row.id, "name": row.name, "base_url": row.base_url} for row in rows]


@router.post("/run")
def ingest_url(
    payload: IngestRequest,
    user: User = Depends(require_roles("Admin", "Curator")),
    db: Session = Depends(get_db),
):
    compliance = resolve_sensitive_action_compliance(
        db=db,
        user=user,
        action_type="ingest.run",
        operation_id=payload.operation_id,
        compliance_confirmed=payload.compliance_confirmed,
        compliance_reason=payload.compliance_reason,
        compliance_bypassed=payload.compliance_bypassed,
    )

    _validate_url_or_422(payload.url)
    source = db.get(Source, payload.source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    _validate_source_permission_or_422(source)
    _validate_ingest_url_matches_source_or_422(source, payload.url)

    try:
        result = run_ingest(db=db, source_id=payload.source_id, url=payload.url)
    except Exception as exc:
        logger.exception("Ingest failed for source %d", payload.source_id)
        model_usage = ingest_model_usage(embedding_used=False, vision_used=None)
        write_audit(
            db,
            action="ingest.failed",
            object_ref=f"source:{payload.source_id}",
            user_id=user.id,
            metadata={
                "error": str(exc),
                "operation_id": compliance.operation_id,
                "batch_id": payload.batch_id,
                "row_id": payload.row_id,
                "compliance_confirmed": compliance.compliance_confirmed,
                "compliance_bypassed": compliance.compliance_bypassed,
                "compliance_reason": compliance.compliance_reason,
                "model_usage": model_usage,
            },
        )
        try:
            db.commit()
        except Exception:
            db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    action = "ingest.blocked" if result.get("status") == "blocked_captcha" else "ingest.completed"
    model_usage = result.get("model_usage") or ingest_model_usage(
        embedding_used=result.get("status") == "completed",
        vision_used=None,
    )
    write_audit(
        db,
        action=action,
        object_ref=f"source:{payload.source_id}",
        user_id=user.id,
        metadata={
            **result,
            "operation_id": compliance.operation_id,
            "batch_id": payload.batch_id,
            "row_id": payload.row_id,
            "compliance_confirmed": compliance.compliance_confirmed,
            "compliance_bypassed": compliance.compliance_bypassed,
            "compliance_reason": compliance.compliance_reason,
            "model_usage": model_usage,
        },
    )
    db.commit()
    return {
        **result,
        "operation_id": compliance.operation_id,
        "batch_id": payload.batch_id,
        "row_id": payload.row_id,
        "compliance_confirmed": compliance.compliance_confirmed,
        "compliance_bypassed": compliance.compliance_bypassed,
        "compliance_reason": compliance.compliance_reason,
        "model_usage": model_usage,
    }


@router.post("/refresh")
def refresh_url(
    payload: RefreshRequest,
    user: User = Depends(require_roles("Admin", "Curator")),
    db: Session = Depends(get_db),
):
    compliance = resolve_sensitive_action_compliance(
        db=db,
        user=user,
        action_type="ingest.refresh",
        operation_id=payload.operation_id,
        compliance_confirmed=payload.compliance_confirmed,
        compliance_reason=payload.compliance_reason,
        compliance_bypassed=payload.compliance_bypassed,
    )

    _validate_url_or_422(payload.url)
    source = db.get(Source, payload.source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    _validate_source_permission_or_422(source)
    _validate_ingest_url_matches_source_or_422(source, payload.url)

    existing = (
        db.query(Document)
        .filter(Document.source_id == payload.source_id, Document.url == payload.url)
        .first()
    )
    if not existing:
        raise HTTPException(status_code=404, detail="URL has not been ingested yet. Use /api/ingest/run first.")

    outcome = run_refresh(
        db,
        source_id=payload.source_id,
        url=payload.url,
        refresh_interval_minutes=payload.refresh_interval_minutes,
        trigger="manual",
    )

    status = outcome.status
    action = "refresh.completed" if status == "completed" else "refresh.skipped" if status.startswith("skipped") else "refresh.failed"
    model_usage = ingest_model_usage(embedding_used=status == "completed", vision_used=None)
    write_audit(
        db,
        action=action,
        object_ref=f"source:{payload.source_id}",
        user_id=user.id,
        metadata={
            "status": status,
            "job_id": outcome.job_id,
            "error": outcome.error,
            "url": payload.url,
            "refresh_interval_minutes": payload.refresh_interval_minutes,
            "operation_id": compliance.operation_id,
            "batch_id": payload.batch_id,
            "row_id": payload.row_id,
            "compliance_confirmed": compliance.compliance_confirmed,
            "compliance_bypassed": compliance.compliance_bypassed,
            "compliance_reason": compliance.compliance_reason,
            "model_usage": model_usage,
        },
    )
    db.commit()
    return {
        "status": status,
        "job_id": outcome.job_id,
        "error": outcome.error,
        "operation_id": compliance.operation_id,
        "batch_id": payload.batch_id,
        "row_id": payload.row_id,
        "compliance_confirmed": compliance.compliance_confirmed,
        "compliance_bypassed": compliance.compliance_bypassed,
        "compliance_reason": compliance.compliance_reason,
        "model_usage": model_usage,
    }
