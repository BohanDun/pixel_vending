"""add daily summaries

Revision ID: da91e63b4f20
Revises: f4c821d9307a
Create Date: 2026-07-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "da91e63b4f20"
down_revision: Union[str, Sequence[str], None] = "f4c821d9307a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "daily_summaries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("summary_date", sa.Date(), nullable=False),
        sa.Column(
            "total_revenue",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
        ),
        sa.Column("successful_transactions", sa.Integer(), nullable=False),
        sa.Column("failed_transactions", sa.Integer(), nullable=False),
        sa.Column("units_sold", sa.Integer(), nullable=False),
        sa.Column("top_product_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["top_product_id"],
            ["products.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "summary_date",
            name="uq_daily_summary_user_date",
        ),
    )
    op.create_index(
        op.f("ix_daily_summaries_id"),
        "daily_summaries",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_daily_summaries_summary_date"),
        "daily_summaries",
        ["summary_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_daily_summaries_user_id"),
        "daily_summaries",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_transactions_user_created",
        "transactions",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_transactions_user_status_created",
        "transactions",
        ["user_id", "status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_transactions_user_status_created",
        table_name="transactions",
    )
    op.drop_index(
        "ix_transactions_user_created",
        table_name="transactions",
    )
    op.drop_index(
        op.f("ix_daily_summaries_user_id"),
        table_name="daily_summaries",
    )
    op.drop_index(
        op.f("ix_daily_summaries_summary_date"),
        table_name="daily_summaries",
    )
    op.drop_index(
        op.f("ix_daily_summaries_id"),
        table_name="daily_summaries",
    )
    op.drop_table("daily_summaries")
