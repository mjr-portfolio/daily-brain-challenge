"""add server-only puzzle solution and explanation

Revision ID: 20261005_0002
Revises: 20260310_0001
Create Date: 2026-10-05 22:45:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261005_0002"
down_revision: Union[str, Sequence[str], None] = "20260310_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "puzzles",
        sa.Column("solution", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column("puzzles", sa.Column("explanation", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("puzzles", "explanation")
    op.drop_column("puzzles", "solution")
