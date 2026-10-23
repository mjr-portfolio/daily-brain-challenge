"""store the best daily streak on the account

Revision ID: 20261022_0005
Revises: 20261021_0004
Create Date: 2026-10-22 21:50:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261022_0005"
down_revision: Union[str, Sequence[str], None] = "20261021_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("best_streak", sa.Integer(), nullable=False, server_default="0"),
    )
    op.execute("UPDATE users SET best_streak = streak_count")


def downgrade() -> None:
    op.drop_column("users", "best_streak")
