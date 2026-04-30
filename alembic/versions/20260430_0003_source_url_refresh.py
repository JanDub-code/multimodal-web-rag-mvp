"""add source url refresh metadata

Revision ID: 20260430_0003
Revises: 20260430_0002
Create Date: 2026-04-30 12:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260430_0003"
down_revision: Union[str, Sequence[str], None] = "20260430_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "source_urls",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("refresh_interval_minutes", sa.Integer(), nullable=True),
        sa.Column("last_successful_ingest_ts", sa.DateTime(), nullable=True),
        sa.Column("last_attempt_ts", sa.DateTime(), nullable=True),
        sa.Column("created_ts", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_source_urls_source_url", "source_urls", ["source_id", "url"], unique=True)
    op.create_index("ix_source_urls_source_id", "source_urls", ["source_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_source_urls_source_id", table_name="source_urls")
    op.drop_index("ix_source_urls_source_url", table_name="source_urls")
    op.drop_table("source_urls")
