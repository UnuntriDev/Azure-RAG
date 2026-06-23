"""add user_id to documents, conversations, query_logs

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-18

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("user_id", sa.String(128), nullable=True))
    op.create_index("ix_documents_user_id_created_at", "documents", ["user_id", "created_at"])

    op.add_column("conversations", sa.Column("user_id", sa.String(128), nullable=True))
    op.create_index(
        "ix_conversations_user_id_updated_at",
        "conversations",
        ["user_id", sa.text("updated_at DESC")],
    )

    op.add_column("query_logs", sa.Column("user_id", sa.String(128), nullable=True))
    op.create_index(
        "ix_query_logs_user_id_created_at",
        "query_logs",
        ["user_id", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_query_logs_user_id_created_at", table_name="query_logs")
    op.drop_column("query_logs", "user_id")

    op.drop_index("ix_conversations_user_id_updated_at", table_name="conversations")
    op.drop_column("conversations", "user_id")

    op.drop_index("ix_documents_user_id_created_at", table_name="documents")
    op.drop_column("documents", "user_id")
