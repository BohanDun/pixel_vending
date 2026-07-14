from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

DATABASE_PATH = Path(__file__).resolve().parent.parent / 'vending_machine.db'
SQL_ALCHEMY_DATABASE_URL = f'sqlite:///{DATABASE_PATH}'

engine = create_engine(SQL_ALCHEMY_DATABASE_URL, connect_args={'check_same_thread': False})
SessionLocal = sessionmaker(autocommit = False, autoflush = False, bind = engine)

Base = declarative_base()

def ensure_product_columns():
    with engine.begin() as connection:
        existing_columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info(products)"))
        }

        if "quantity" not in existing_columns:
            connection.execute(
                text("ALTER TABLE products ADD COLUMN quantity INTEGER NOT NULL DEFAULT 0")
            )

        if "price" not in existing_columns:
            connection.execute(
                text("ALTER TABLE products ADD COLUMN price NUMERIC(10, 2) NOT NULL DEFAULT 0.00")
            )

def ensure_machine_product_columns():
    with engine.begin() as connection:
        existing_columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info(machine_products)"))
        }

        if "quantity" not in existing_columns:
            connection.execute(
                text("ALTER TABLE machine_products ADD COLUMN quantity INTEGER NOT NULL DEFAULT 0")
            )

        # Older versions could insert the same product into a machine more than once.
        # Preserve the inventory by summing those rows before enforcing uniqueness.
        connection.execute(
            text(
                """
                UPDATE machine_products AS machine_product
                SET quantity = (
                    SELECT SUM(duplicate.quantity)
                    FROM machine_products AS duplicate
                    WHERE duplicate.machine_id = machine_product.machine_id
                      AND duplicate.product_id = machine_product.product_id
                )
                WHERE rowid IN (
                    SELECT MIN(rowid)
                    FROM machine_products
                    GROUP BY machine_id, product_id
                )
                """
            )
        )
        connection.execute(
            text(
                """
                DELETE FROM machine_products
                WHERE rowid NOT IN (
                    SELECT MIN(rowid)
                    FROM machine_products
                    GROUP BY machine_id, product_id
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_machine_product
                ON machine_products (machine_id, product_id)
                """
            )
        )
