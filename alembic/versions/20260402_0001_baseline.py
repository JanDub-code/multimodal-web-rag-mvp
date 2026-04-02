"""baseline schema

Revision ID: 20260402_0001
Revises:
Create Date: 2026-04-02 16:40:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260402_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("created_ts", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("issued_ts", sa.DateTime(), nullable=False),
        sa.Column("expires_ts", sa.DateTime(), nullable=False),
        sa.Column("revoked_ts", sa.DateTime(), nullable=True),
        sa.Column("replaced_by_token_hash", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"], unique=False)
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)
    op.create_index(op.f("ix_refresh_tokens_expires_ts"), "refresh_tokens", ["expires_ts"], unique=False)

    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("base_url", sa.String(length=1000), nullable=False),
        sa.Column("permission_type", sa.String(length=100), nullable=False),
        sa.Column("permission_ref", sa.String(length=255), nullable=True),
        sa.Column("crawl_rules", sa.Text(), nullable=True),
        sa.Column("retention_rules", sa.Text(), nullable=True),
        sa.Column("created_ts", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sources_id"), "sources", ["id"], unique=False)

    op.create_table(
        "ingest_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("strategy", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("started_ts", sa.DateTime(), nullable=False),
        sa.Column("finished_ts", sa.DateTime(), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ingest_jobs_source_id"), "ingest_jobs", ["source_id"], unique=False)

    op.create_table(
        "evidence",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("storage_uri", sa.String(length=1200), nullable=False),
        sa.Column("hash", sa.String(length=128), nullable=False),
        sa.Column("created_ts", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("doc_version", sa.Integer(), nullable=False),
        sa.Column("content_structured_uri", sa.String(length=1200), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=False),
        sa.Column("created_ts", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_documents_url"), "documents", ["url"], unique=False)
    op.create_index("ix_documents_source_url", "documents", ["source_id", "url"], unique=False)

    op.create_table(
        "chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("doc_id", sa.Integer(), nullable=False),
        sa.Column("chunk_type", sa.String(length=50), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("citations_ref", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["doc_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_chunks_doc_id"), "chunks", ["doc_id"], unique=False)

    op.create_table(
        "embeddings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chunk_id", sa.Integer(), nullable=False),
        sa.Column("model_id", sa.String(length=255), nullable=False),
        sa.Column("vector_ref", sa.String(length=255), nullable=False),
        sa.Column("created_ts", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["chunk_id"], ["chunks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_embeddings_chunk_id"), "embeddings", ["chunk_id"], unique=False)

    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_ts", sa.DateTime(), nullable=False),
        sa.Column("resolved_ts", sa.DateTime(), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("evidence_refs", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("object_ref", sa.String(length=255), nullable=False),
        sa.Column("ts", sa.DateTime(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_user_ts", "audit_logs", ["user_id", "ts"], unique=False)
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_action"), table_name="audit_logs")
    op.drop_index("ix_audit_logs_user_ts", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_table("incidents")

    op.drop_index(op.f("ix_embeddings_chunk_id"), table_name="embeddings")
    op.drop_table("embeddings")

    op.drop_index(op.f("ix_chunks_doc_id"), table_name="chunks")
    op.drop_table("chunks")

    op.drop_index("ix_documents_source_url", table_name="documents")
    op.drop_index(op.f("ix_documents_url"), table_name="documents")
    op.drop_table("documents")

    op.drop_table("evidence")

    op.drop_index(op.f("ix_ingest_jobs_source_id"), table_name="ingest_jobs")
    op.drop_table("ingest_jobs")

    op.drop_index(op.f("ix_sources_id"), table_name="sources")
    op.drop_table("sources")

    op.drop_index(op.f("ix_refresh_tokens_expires_ts"), table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_token_hash", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")

    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")
