import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.database import Base
from api.models import (
    Machine,
    MachineProduct,
    Product,
    Transaction,
    TransactionStatus,
    User,
)
from api.services.simulation_service import SimulationService


class FixedRandom:
    def choice(self, items):
        return items[0]

    def randint(self, start, end):
        return end

    def sample(self, items, count):
        return items[:count]


class SimulationServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_directory.name) / "test.db"
        engine = create_engine(
            f"sqlite:///{database_path}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=engine)
        self.session = sessionmaker(bind=engine)()

        user = User(username="simulation-user", hashed_password="not-used")
        self.session.add(user)
        self.session.flush()
        self.user_id = user.id

    def tearDown(self):
        self.session.close()
        self.temp_directory.cleanup()

    def test_run_once_can_purchase_from_multiple_machines(self):
        product = Product(
            user_id=self.user_id,
            name="Water",
            description="Test water",
            quantity=50,
            price=Decimal("2.00"),
        )
        second_product = Product(
            user_id=self.user_id,
            name="Cookies",
            description="Test cookies",
            quantity=50,
            price=Decimal("1.00"),
        )
        machine = Machine(
            user_id=self.user_id,
            name="Pixel Machine",
            description="Test",
        )
        second_machine_product = Product(
            user_id=self.user_id,
            name="Coke",
            description="Test coke",
            quantity=50,
            price=Decimal("1.00"),
        )
        second_machine = Machine(
            user_id=self.user_id,
            name="Second Machine",
            description="Test",
        )
        self.session.add_all(
            [
                product,
                second_product,
                second_machine_product,
                machine,
                second_machine,
            ]
        )
        self.session.flush()
        self.session.add(
            MachineProduct(
                machine_id=machine.id,
                product_id=product.id,
                quantity=5,
                capacity=20,
                auto_restock_enabled=False,
            )
        )
        self.session.add(
            MachineProduct(
                machine_id=second_machine.id,
                product_id=second_machine_product.id,
                quantity=4,
                capacity=20,
                auto_restock_enabled=False,
            )
        )
        self.session.add(
            MachineProduct(
                machine_id=machine.id,
                product_id=second_product.id,
                quantity=4,
                capacity=20,
                auto_restock_enabled=False,
            )
        )
        self.session.commit()

        result = SimulationService(FixedRandom()).run_once(
            db=self.session,
            user_id=self.user_id,
        )

        self.assertTrue(result["customer"].customer_id.startswith("CUST-"))
        self.assertEqual(result["customer"].name, "Mia")
        self.assertEqual(len(result["purchases"]), 3)
        self.assertEqual(
            {purchase["machine_id"] for purchase in result["purchases"]},
            {machine.id, second_machine.id},
        )
        self.assertEqual(
            [purchase["product_name"] for purchase in result["purchases"]],
            ["Water", "Cookies", "Coke"],
        )
        self.assertEqual(
            result["purchases"][0]["transaction"].status,
            TransactionStatus.SUCCESS,
        )
        self.assertEqual(
            self.session.get(
                MachineProduct,
                (machine.id, product.id),
            ).quantity,
            2,
        )
        self.assertEqual(
            self.session.get(
                MachineProduct,
                (machine.id, second_product.id),
            ).quantity,
            1,
        )
        self.assertEqual(
            self.session.get(
                MachineProduct,
                (second_machine.id, second_machine_product.id),
            ).quantity,
            1,
        )
        self.assertEqual(self.session.query(Transaction).count(), 3)

    def test_run_once_requires_a_machine_with_products(self):
        with self.assertRaisesRegex(
            ValueError,
            "No machine is available",
        ):
            SimulationService(FixedRandom()).run_once(
                db=self.session,
                user_id=self.user_id,
            )

    def test_run_once_records_stockout_then_refills_machine(self):
        product = Product(
            user_id=self.user_id,
            name="Empty Chips",
            description="Test stockout",
            quantity=0,
            price=Decimal("2.00"),
        )
        machine = Machine(
            user_id=self.user_id,
            name="Empty Machine",
            description="Test",
        )
        self.session.add_all([product, machine])
        self.session.flush()
        self.session.add(
            MachineProduct(
                machine_id=machine.id,
                product_id=product.id,
                quantity=0,
                capacity=50,
                auto_restock_enabled=True,
            )
        )
        self.session.commit()

        result = SimulationService(FixedRandom()).run_once(
            db=self.session,
            user_id=self.user_id,
        )

        self.assertEqual(
            result["purchases"][0]["transaction"].status,
            TransactionStatus.OUT_OF_STOCK,
        )
        self.assertEqual(
            self.session.get(
                MachineProduct,
                (machine.id, product.id),
            ).quantity,
            50,
        )
        self.assertEqual(self.session.get(Product, product.id).quantity, 50)


if __name__ == "__main__":
    unittest.main()
