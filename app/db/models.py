from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    created_ts: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    permission_type: Mapped[str] = mapped_column(String(100), default="public")
    permission_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    crawl_rules: Mapped[str | None] = mapped_column(Text, nullable=True)
    retention_rules: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_ts: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class IngestJob(Base):
    __tablename__ = "ingest_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    strategy: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    started_ts: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    finished_ts: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(1200), nullable=False)
    hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_ts: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_source_url", "source_id", "url"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False, index=True)
    doc_version: Mapped[int] = mapped_column(Integer, default=1)
    content_structured_uri: Mapped[str] = mapped_column(String(1200), nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_ts: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doc_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_type: Mapped[str] = mapped_column(String(50), default="text")
    text: Mapped[str] = mapped_column(Text, nullable=False)
    citations_ref: Mapped[str] = mapped_column(Text, nullable=False)

    document: Mapped[Document] = relationship(back_populates="chunks")


class Embedding(Base):
    __tablename__ = "embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chunk_id: Mapped[int] = mapped_column(ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False, index=True)
    model_id: Mapped[str] = mapped_column(String(255), nullable=False)
    vector_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    created_ts: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(50), default="captcha")
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="medium")
    status: Mapped[str] = mapped_column(String(50), default="open")
    created_ts: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    resolved_ts: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_refs: Mapped[str] = mapped_column(Text, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_user_ts", "user_id", "ts"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    object_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
