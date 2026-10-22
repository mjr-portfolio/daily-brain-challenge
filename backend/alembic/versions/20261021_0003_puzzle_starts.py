"""record when a signed-in player starts a puzzle

Revision ID: 20261021_0003
Revises: 20261005_0002
Create Date: 2026-10-21 12:40:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261021_0003"
down_revision: Union[str, Sequence[str], None] = "20261005_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "puzzle_starts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("puzzle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["puzzle_id"], ["puzzles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "puzzle_id", name="uq_puzzle_starts_user_puzzle"),
    )
    op.create_index("ix_puzzle_starts_user_id", "puzzle_starts", ["user_id"], unique=False)
    op.create_index("ix_puzzle_starts_puzzle_id", "puzzle_starts", ["puzzle_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_puzzle_starts_puzzle_id", table_name="puzzle_starts")
    op.drop_index("ix_puzzle_starts_user_id", table_name="puzzle_starts")
    op.drop_table("puzzle_starts")
