"""add transactions

Revision ID: c0a2f4175e31
Revises: 801530de1f14
Create Date: 2026-07-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c0a2f4175e31"
down_revision: Union[str, Sequence[str], None] = "801530de1f14"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("machine_id", sa.Integer(), nullable=True),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("customer_id", sa.String(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("total_price", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "SUCCESS",
                "OUT_OF_STOCK",
                "INSUFFICIENT_BUDGET",
                "INVALID_PRODUCT",
                "FAILED",
                name="transaction_status",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("failure_reason", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["machine_id"],
            ["machines.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_transactions_created_at"),
        "transactions",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_transactions_customer_id"),
        "transactions",
        ["customer_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_transactions_id"),
        "transactions",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_transactions_machine_id"),
        "transactions",
        ["machine_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_transactions_product_id"),
        "transactions",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_transactions_status"),
        "transactions",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_transactions_user_id"),
        "transactions",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_transactions_user_id"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_status"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_product_id"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_machine_id"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_id"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_customer_id"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_created_at"), table_name="transactions")
    op.drop_table("transactions")
