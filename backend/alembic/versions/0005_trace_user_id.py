"""add user_id to traces

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-22

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("traces", sa.Column("user_id", sa.String(128), nullable=True))
    op.create_index(
        "ix_traces_user_id_created_at",
        "traces",
        ["user_id", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_traces_user_id_created_at", table_name="traces")
    op.drop_column("traces", "user_id")
