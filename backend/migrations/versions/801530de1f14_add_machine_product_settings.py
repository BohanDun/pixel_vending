"""add machine product settings

Revision ID: 801530de1f14
Revises: 9f6e890779cd
Create Date: 2026-07-14 23:17:30.010711

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '801530de1f14'
down_revision: Union[str, Sequence[str], None] = '9f6e890779cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # A pre-Alembic helper may have created this redundant explicit index.
    # The initial migration itself only creates the named unique constraint.
    index_names = {
        index["name"]
        for index in sa.inspect(op.get_bind()).get_indexes("machine_products")
    }
    if "uq_machine_product" in index_names:
        op.drop_index("uq_machine_product", table_name="machine_products")

    # SQLite cannot add a primary key to an existing table in place. Batch mode
    # recreates the table and copies existing quantities into the new schema.
    with op.batch_alter_table("machine_products", recreate="always") as batch_op:
        batch_op.add_column(
            sa.Column("capacity", sa.Integer(), server_default="20", nullable=False)
        )
        batch_op.add_column(
            sa.Column(
                "low_stock_threshold",
                sa.Integer(),
                server_default="5",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "auto_restock_enabled",
                sa.Boolean(),
                server_default="1",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column("last_restocked_at", sa.DateTime(), nullable=True)
        )
        batch_op.alter_column(
            "machine_id", existing_type=sa.Integer(), nullable=False
        )
        batch_op.alter_column(
            "product_id", existing_type=sa.Integer(), nullable=False
        )
        batch_op.drop_constraint("uq_machine_product", type_="unique")
        batch_op.create_primary_key(
            "pk_machine_products", ["machine_id", "product_id"]
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("machine_products", recreate="always") as batch_op:
        batch_op.drop_constraint("pk_machine_products", type_="primary")
        batch_op.create_unique_constraint(
            "uq_machine_product", ["machine_id", "product_id"]
        )
        batch_op.alter_column(
            "product_id", existing_type=sa.Integer(), nullable=True
        )
        batch_op.alter_column(
            "machine_id", existing_type=sa.Integer(), nullable=True
        )
        batch_op.drop_column("last_restocked_at")
        batch_op.drop_column("auto_restock_enabled")
        batch_op.drop_column("low_stock_threshold")
        batch_op.drop_column("capacity")
