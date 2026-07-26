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
from api.schemas.transaction import PurchaseRequest
from api.services import PurchaseService


class PurchaseServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_directory.name) / "test.db"
        engine = create_engine(
            f"sqlite:///{database_path}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=engine)
        self.session = sessionmaker(bind=engine)()

        user = User(username="purchase-user", hashed_password="not-used")
        self.session.add(user)
        self.session.flush()

        product = Product(
            user_id=user.id,
            name="Cola",
            description="Test drink",
            quantity=50,
            price=Decimal("3.50"),
        )
        machine = Machine(
            user_id=user.id,
            name="Purchase Machine",
            description="Test",
        )
        self.session.add_all([product, machine])
        self.session.flush()

        machine_product = MachineProduct(
            machine_id=machine.id,
            product_id=product.id,
            quantity=5,
            capacity=20,
        )
        self.session.add(machine_product)
        self.session.commit()

        self.user_id = user.id
        self.product_id = product.id
        self.machine_id = machine.id

    def tearDown(self):
        self.session.close()
        self.temp_directory.cleanup()

    def machine_product(self):
        return self.session.get(
            MachineProduct,
            (self.machine_id, self.product_id),
        )

    def purchase(self, quantity: int, budget: str):
        return PurchaseService.purchase(
            db=self.session,
            user_id=self.user_id,
            machine_id=self.machine_id,
            product_id=self.product_id,
            payload=PurchaseRequest(
                customer_id="CUST-001",
                quantity=quantity,
                budget=Decimal(budget),
            ),
        )

    def test_successful_purchase_reduces_stock_and_records_transaction(self):
        transaction = self.purchase(quantity=2, budget="10.00")

        self.assertEqual(transaction.status, TransactionStatus.SUCCESS)
        self.assertEqual(transaction.unit_price, Decimal("3.50"))
        self.assertEqual(transaction.total_price, Decimal("7.00"))
        self.assertEqual(self.machine_product().quantity, 3)
        self.assertEqual(self.session.query(Transaction).count(), 1)

    def test_out_of_stock_purchase_keeps_stock_and_records_failure(self):
        transaction = self.purchase(quantity=6, budget="30.00")

        self.assertEqual(transaction.status, TransactionStatus.OUT_OF_STOCK)
        self.assertEqual(transaction.failure_reason, "Not enough machine stock")
        self.assertEqual(self.machine_product().quantity, 5)
        self.assertEqual(self.session.query(Transaction).count(), 1)

    def test_insufficient_budget_keeps_stock_and_records_failure(self):
        transaction = self.purchase(quantity=2, budget="5.00")

        self.assertEqual(
            transaction.status,
            TransactionStatus.INSUFFICIENT_BUDGET,
        )
        self.assertEqual(
            transaction.failure_reason,
            "Customer budget is insufficient",
        )
        self.assertEqual(self.machine_product().quantity, 5)
        self.assertEqual(self.session.query(Transaction).count(), 1)


if __name__ == "__main__":
    unittest.main()
