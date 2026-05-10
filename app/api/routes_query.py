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


QUERY_MODEL_OPTIONS = {
    "opencode-go/deepseek-v4-flash": "DeepSeek V4 Flash",
    "opencode-go/minimax-m2.7": "MiniMax M2.7",
    "opencode-go/minimax-m2.5": "MiniMax M2.5",
    "opencode-go/kimi-k2.5": "Kimi K2.5 Vision",
}


class QueryMode(str, Enum):
    rag = "rag"
    no_rag = "no-rag"


class ConversationMessage(BaseModel):
    role: str = Field(..., max_length=20)
    content: str = Field(..., max_length=4000)


class QueryRequest(BaseModel):
    query: str = Field(..., max_length=1000)
    mode: QueryMode = QueryMode.rag
    top_k: int = Field(default=5, ge=1, le=20)
    operation_id: str | None = Field(default=None, max_length=160)
    compliance_confirmed: bool | None = None
    compliance_reason: str | None = Field(default=None, max_length=500)
    compliance_bypassed: bool | None = None
    model: str | None = Field(default=None, max_length=120)
    conversation_history: list[ConversationMessage] = Field(default_factory=list, max_length=16)


@router.get("/models")
def query_models(_user: User = Depends(require_roles("Admin", "Curator", "Analyst", "User"))):
    return [{"label": label, "value": value} for value, label in QUERY_MODEL_OPTIONS.items()]


@router.post("/")
def ask(
    payload: QueryRequest,
    user: User = Depends(require_roles("Admin", "Curator", "Analyst", "User")),
    db: Session = Depends(get_db),
):
    selected_model = payload.model.strip() if payload.model else None
    if selected_model and selected_model not in QUERY_MODEL_OPTIONS:
        selected_model = None
    conversation_history = [
        message.model_dump()
        for message in payload.conversation_history
        if message.content.strip() and message.role.strip()
    ]

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
        answer = answer_no_rag(
            payload.query,
            db=db,
            user_id=user.id,
            model=selected_model,
            conversation_history=conversation_history,
        )
        model_usage = query_model_usage(mode=QueryMode.no_rag.value, generation_model=selected_model)
        response = {
            "mode": QueryMode.no_rag.value,
            "answer": answer,
            "citations": [],
            "model_usage": model_usage,
        }
    else:
        retrieved = search_top_k(db, payload.query, top_k=payload.top_k)
        rag = answer_rag(
            payload.query,
            retrieved,
            db=db,
            user_id=user.id,
            model=selected_model,
            conversation_history=conversation_history,
        )
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
            "selected_model": selected_model,
            "conversation_history_count": len(conversation_history),
        },
    )
    db.commit()
    return {
        **response,
        "selected_model": selected_model,
        "operation_id": compliance.operation_id,
        "compliance_confirmed": compliance.compliance_confirmed,
        "compliance_bypassed": compliance.compliance_bypassed,
        "compliance_reason": compliance.compliance_reason,
    }
