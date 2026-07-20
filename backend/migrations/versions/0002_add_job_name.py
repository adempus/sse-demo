"""add name to job

Revision ID: 0002_add_job_name
Revises: 0001_baseline
Create Date: 2026-07-04

Adds a required ``name`` column to ``job`` and indexes it. Existing rows are
backfilled with a server default so the NOT NULL constraint holds.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_add_job_name"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("job") as batch_op:
        batch_op.add_column(
            sa.Column(
                "name",
                sa.String(length=120),
                nullable=False,
                server_default="Untitled Job",
            )
        )
        batch_op.create_index("ix_job_name", ["name"])


def downgrade() -> None:
    with op.batch_alter_table("job") as batch_op:
        batch_op.drop_index("ix_job_name")
        batch_op.drop_column("name")
