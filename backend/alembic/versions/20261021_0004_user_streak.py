"""store a daily streak on the account

Revision ID: 20261021_0004
Revises: 20261021_0003
Create Date: 2026-10-21 13:20:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261021_0004"
down_revision: Union[str, Sequence[str], None] = "20261021_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("streak_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("users", sa.Column("streak_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "streak_date")
    op.drop_column("users", "streak_count")
