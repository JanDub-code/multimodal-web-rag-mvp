from enum import Enum

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.routes_auth import require_roles
from app.db.models import User
from app.db.session import get_db
from app.services.answering import answer_no_rag, answer_rag
from app.services.audit import write_audit
from app.services.retrieval import search_top_k


router = APIRouter(prefix="/api/query", tags=["query"])


class QueryMode(str, Enum):
    rag = "rag"
    no_rag = "no-rag"


class QueryRequest(BaseModel):
    query: str = Field(..., max_length=1000)
    mode: QueryMode = QueryMode.rag
    top_k: int = Field(default=5, ge=1, le=20)


@router.post("/")
def ask(
    payload: QueryRequest,
    user: User = Depends(require_roles("Admin", "Curator", "Analyst", "User")),
    db: Session = Depends(get_db),
):
    if payload.mode == QueryMode.no_rag:
        answer = answer_no_rag(payload.query)
        response = {"mode": QueryMode.no_rag.value, "answer": answer, "citations": []}
    else:
        retrieved = search_top_k(payload.query, top_k=payload.top_k)
        rag = answer_rag(payload.query, retrieved)
        response = {"mode": QueryMode.rag.value, **rag}

    write_audit(
        db,
        action="query.executed",
        object_ref="query",
        user_id=user.id,
        metadata={"mode": payload.mode.value, "query": payload.query[:300]},
    )
    db.commit()
    return response
