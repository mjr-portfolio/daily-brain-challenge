"""account credentials, handle, theme, and refresh token

Revision ID: 20261024_0006
Revises: 20261022_0005
Create Date: 2026-10-24 00:20:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261024_0006"
down_revision: Union[str, Sequence[str], None] = "20261022_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("display_name", sa.String(length=32), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "preferences",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column("users", sa.Column("refresh_token_hash", sa.String(length=64), nullable=True))
    op.add_column(
        "users",
        sa.Column("refresh_token_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint(
        "uq_users_refresh_token_hash",
        "users",
        ["refresh_token_hash"],
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_users_display_name_lower ON users (lower(display_name))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_users_display_name_lower")
    op.drop_constraint("uq_users_refresh_token_hash", "users", type_="unique")
    op.drop_column("users", "refresh_token_expires_at")
    op.drop_column("users", "refresh_token_hash")
    op.drop_column("users", "preferences")
    op.drop_column("users", "display_name")
    op.drop_column("users", "password_hash")
