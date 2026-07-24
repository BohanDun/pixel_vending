import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.database import Base
from api.models import Machine, MachineProduct, Product, User
from api.routers.machines import (
    add_product_to_machine,
    delete_machine,
    delete_machine_product_quantity,
    put_machine_product_quantity_back,
    update_machine_product_quantity,
)
from api.routers.products import restock_product
from api.schemas.machine import MachineProductQuantity
from api.schemas.product import ProductQuantityChange


class InventoryFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_directory.name) / "test.db"
        engine = create_engine(
            f"sqlite:///{database_path}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=engine)
        self.session = sessionmaker(bind=engine)()

        user = User(username="test-user", hashed_password="not-used")
        product = Product(
            user_id=1,
            name="Test Product",
            description="Inventory flow test",
            quantity=100,
            price=2,
        )
        machine = Machine(user_id=1, name="Test Machine", description="Test")
        self.session.add_all([user, product, machine])
        self.session.commit()

        self.user = {"id": user.id}
        self.product_id = product.id
        self.machine_id = machine.id

    def tearDown(self):
        self.session.close()
        self.temp_directory.cleanup()

    def product(self):
        return self.session.get(Product, self.product_id)

    def machine_product(self):
        return self.session.get(
            MachineProduct,
            (self.machine_id, self.product_id),
        )

    def test_existing_inventory_operations(self):
        # Add stock to the warehouse.
        restock_product(
            self.session,
            self.user,
            self.product_id,
            ProductQuantityChange(quantity=20),
        )
        self.assertEqual(self.product().quantity, 120)

        # Move warehouse stock into the machine.
        add_product_to_machine(
            self.session,
            self.user,
            self.machine_id,
            self.product_id,
            MachineProductQuantity(quantity=20),
        )
        self.assertEqual(self.product().quantity, 100)
        self.assertEqual(self.machine_product().quantity, 20)

        # Sell machine stock. Sold stock is not returned to the warehouse.
        delete_machine_product_quantity(
            self.session,
            self.user,
            self.machine_id,
            self.product_id,
            MachineProductQuantity(quantity=8),
        )
        self.assertEqual(self.product().quantity, 100)
        self.assertEqual(self.machine_product().quantity, 12)

        # Return machine stock to the warehouse.
        put_machine_product_quantity_back(
            self.session,
            self.user,
            self.machine_id,
            self.product_id,
            MachineProductQuantity(quantity=7),
        )
        self.assertEqual(self.product().quantity, 107)
        self.assertEqual(self.machine_product().quantity, 5)

        # Deleting a machine returns all remaining stock to the warehouse.
        delete_machine(self.session, self.user, self.machine_id)
        self.assertEqual(self.product().quantity, 112)
        self.assertIsNone(self.session.get(Machine, self.machine_id))
        self.assertIsNone(self.machine_product())

    def test_cannot_exceed_machine_product_capacity(self):
        with self.assertRaises(HTTPException) as context:
            add_product_to_machine(
                self.session,
                self.user,
                self.machine_id,
                self.product_id,
                MachineProductQuantity(quantity=21),
            )

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(
            context.exception.detail,
            "Quantity exceeds machine product capacity",
        )
        self.assertEqual(self.product().quantity, 100)
        self.assertIsNone(self.machine_product())

    def test_reducing_machine_quantity_returns_stock_to_warehouse(self):
        add_product_to_machine(
            self.session,
            self.user,
            self.machine_id,
            self.product_id,
            MachineProductQuantity(quantity=20),
        )

        update_machine_product_quantity(
            self.session,
            self.user,
            self.machine_id,
            self.product_id,
            MachineProductQuantity(quantity=12),
        )

        self.assertEqual(self.product().quantity, 88)
        self.assertEqual(self.machine_product().quantity, 12)

    def test_cannot_sell_more_than_machine_stock(self):
        add_product_to_machine(
            self.session,
            self.user,
            self.machine_id,
            self.product_id,
            MachineProductQuantity(quantity=10),
        )

        with self.assertRaises(HTTPException) as context:
            delete_machine_product_quantity(
                self.session,
                self.user,
                self.machine_id,
                self.product_id,
                MachineProductQuantity(quantity=11),
            )

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.detail, "Not enough machine stock")
        self.assertEqual(self.product().quantity, 90)
        self.assertEqual(self.machine_product().quantity, 10)


if __name__ == "__main__":
    unittest.main()
