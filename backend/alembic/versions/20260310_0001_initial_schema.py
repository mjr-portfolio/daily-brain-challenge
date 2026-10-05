"""initial schema with guest-aware user_completions

Revision ID: 20260310_0001
Revises:
Create Date: 2026-03-10 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260310_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

puzzle_type_enum = postgresql.ENUM(
    "pattern",
    "anagram",
    "news_quiz",
    name="puzzle_type",
    create_type=False,
)


def upgrade() -> None:
    puzzle_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "puzzles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("puzzle_type", puzzle_type_enum, nullable=False),
        sa.Column("assigned_date", sa.Date(), nullable=True),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("solution_hash", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assigned_date"),
    )

    op.create_table(
        "user_completions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("puzzle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("time_taken_seconds", sa.Integer(), nullable=False),
        sa.Column("is_daily_official", sa.Boolean(), nullable=False),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["puzzle_id"], ["puzzles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_user_completions_puzzle_id"),
        "user_completions",
        ["puzzle_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_completions_user_id"),
        "user_completions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_completions_percentile",
        "user_completions",
        ["puzzle_id", "is_daily_official", "time_taken_seconds"],
        unique=False,
    )
    op.create_index(
        "uq_user_completions_user_puzzle",
        "user_completions",
        ["user_id", "puzzle_id"],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_user_completions_user_puzzle",
        table_name="user_completions",
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )
    op.drop_index("ix_user_completions_percentile", table_name="user_completions")
    op.drop_index(op.f("ix_user_completions_user_id"), table_name="user_completions")
    op.drop_index(op.f("ix_user_completions_puzzle_id"), table_name="user_completions")
    op.drop_table("user_completions")
    op.drop_table("puzzles")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    puzzle_type_enum.drop(op.get_bind(), checkfirst=True)
