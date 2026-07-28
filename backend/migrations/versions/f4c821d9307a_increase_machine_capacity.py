"""increase machine capacity

Revision ID: f4c821d9307a
Revises: c0a2f4175e31
Create Date: 2026-07-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4c821d9307a"
down_revision: Union[str, Sequence[str], None] = "c0a2f4175e31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE machine_products SET capacity = 50")
    with op.batch_alter_table("machine_products") as batch_op:
        batch_op.alter_column(
            "capacity",
            existing_type=sa.Integer(),
            server_default="50",
            existing_nullable=False,
        )


def downgrade() -> None:
    op.execute(
        """
        UPDATE machine_products
        SET capacity = CASE
            WHEN quantity > 20 THEN quantity
            ELSE 20
        END
        """
    )
    with op.batch_alter_table("machine_products") as batch_op:
        batch_op.alter_column(
            "capacity",
            existing_type=sa.Integer(),
            server_default="20",
            existing_nullable=False,
        )
