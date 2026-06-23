"""traces table (stage 3: lightweight observability)

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-17

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003"
down_revision: str = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "traces",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("prompt_version", sa.String(length=20), nullable=False),
        sa.Column(
            "spans",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("total_ms", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_traces_created_at", "traces", [sa.text("created_at DESC")])


def downgrade() -> None:
    op.drop_index("ix_traces_created_at", table_name="traces")
    op.drop_table("traces")
