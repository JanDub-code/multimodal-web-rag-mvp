from enum import Enum

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.routes_auth import require_roles
from app.db.models import User
from app.db.session import get_db
from app.services.answering import answer_no_rag, answer_rag
from app.services.audit import write_audit
from app.services.compliance import resolve_sensitive_action_compliance
from app.services.model_usage import query_model_usage
from app.services.retrieval import search_top_k


router = APIRouter(prefix="/api/query", tags=["query"])


class QueryMode(str, Enum):
    rag = "rag"
    no_rag = "no-rag"


class QueryRequest(BaseModel):
    query: str = Field(..., max_length=1000)
    mode: QueryMode = QueryMode.rag
    top_k: int = Field(default=5, ge=1, le=20)
    operation_id: str | None = Field(default=None, max_length=160)
    compliance_confirmed: bool | None = None
    compliance_reason: str | None = Field(default=None, max_length=500)
    compliance_bypassed: bool | None = None


@router.post("/")
def ask(
    payload: QueryRequest,
    user: User = Depends(require_roles("Admin", "Curator", "Analyst", "User")),
    db: Session = Depends(get_db),
):
    compliance = resolve_sensitive_action_compliance(
        db=db,
        user=user,
        action_type="query.execute",
        operation_id=payload.operation_id,
        compliance_confirmed=payload.compliance_confirmed,
        compliance_reason=payload.compliance_reason,
        compliance_bypassed=payload.compliance_bypassed,
    )

    if payload.mode == QueryMode.no_rag:
        answer = answer_no_rag(payload.query, db=db, user_id=user.id)
        model_usage = query_model_usage(mode=QueryMode.no_rag.value)
        response = {
            "mode": QueryMode.no_rag.value,
            "answer": answer,
            "citations": [],
            "model_usage": model_usage,
        }
    else:
        retrieved = search_top_k(payload.query, top_k=payload.top_k)
        rag = answer_rag(payload.query, retrieved, db=db, user_id=user.id)
        model_usage = rag.get("model_usage") or query_model_usage(mode=QueryMode.rag.value)
        response = {"mode": QueryMode.rag.value, **rag}

    write_audit(
        db,
        action="query.executed",
        object_ref="query",
        user_id=user.id,
        metadata={
            "mode": payload.mode.value,
            "query": payload.query[:300],
            "operation_id": compliance.operation_id,
            "compliance_confirmed": compliance.compliance_confirmed,
            "compliance_bypassed": compliance.compliance_bypassed,
            "compliance_reason": compliance.compliance_reason,
            "model_usage": model_usage,
        },
    )
    db.commit()
    return {
        **response,
        "operation_id": compliance.operation_id,
        "compliance_confirmed": compliance.compliance_confirmed,
        "compliance_bypassed": compliance.compliance_bypassed,
        "compliance_reason": compliance.compliance_reason,
    }
