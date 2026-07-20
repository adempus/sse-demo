"""baseline: jobs table

Revision ID: 0001_baseline
Revises:
Create Date: 2026-07-04

Creates the initial ``job`` table. Guarded with an inspector check so it also
works against databases that already have the table from the pre-migration
``SQLModel.metadata.create_all`` startup path.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "job" in inspector.get_table_names():
        # Table already exists (created by legacy create_all) — nothing to do.
        return
    op.create_table(
        "job",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("job")
