"""require a display name on every account

Revision ID: 20261025_0007
Revises: 20261024_0006
Create Date: 2026-10-25 16:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261025_0007"
down_revision: Union[str, Sequence[str], None] = "20261024_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "display_name",
        existing_type=sa.String(length=32),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "display_name",
        existing_type=sa.String(length=32),
        nullable=True,
    )
