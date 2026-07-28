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
from api.routers.transactions import clear_transactions
from api.services import InventoryService, PurchaseService


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
            capacity=50,
            auto_restock_enabled=False,
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

    def product(self):
        return self.session.get(Product, self.product_id)

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

    def test_successful_purchase_does_not_trigger_automatic_restock(self):
        machine_product = self.machine_product()
        machine_product.quantity = 6
        machine_product.low_stock_threshold = 5
        machine_product.auto_restock_enabled = True
        self.session.commit()

        transaction = self.purchase(quantity=1, budget="10.00")

        self.assertEqual(transaction.status, TransactionStatus.SUCCESS)
        self.assertEqual(self.machine_product().quantity, 5)
        self.assertEqual(self.product().quantity, 50)
        self.assertIsNone(self.machine_product().last_restocked_at)

    def test_stockout_triggers_supplier_delivery_and_machine_restock(self):
        machine_product = self.machine_product()
        machine_product.quantity = 2
        machine_product.low_stock_threshold = 2
        machine_product.auto_restock_enabled = True
        self.product().quantity = 4
        self.session.commit()

        transaction = self.purchase(quantity=3, budget="20.00")

        self.assertEqual(transaction.status, TransactionStatus.OUT_OF_STOCK)
        self.assertEqual(self.machine_product().quantity, 50)
        self.assertEqual(self.product().quantity, 52)
        self.assertIsNotNone(self.machine_product().last_restocked_at)

    def test_disabled_automatic_restock_leaves_stock_reduced(self):
        machine_product = self.machine_product()
        machine_product.quantity = 2
        machine_product.low_stock_threshold = 5
        machine_product.auto_restock_enabled = False
        self.session.commit()

        transaction = self.purchase(quantity=1, budget="10.00")

        self.assertEqual(transaction.status, TransactionStatus.SUCCESS)
        self.assertEqual(self.machine_product().quantity, 1)
        self.assertEqual(self.product().quantity, 50)

    def test_inventory_scan_restores_zero_stock_before_simulation(self):
        machine_product = self.machine_product()
        machine_product.quantity = 0
        machine_product.low_stock_threshold = 5
        machine_product.auto_restock_enabled = True
        self.product().quantity = 0
        self.session.commit()

        restocked_items = InventoryService.restock_all_low_stock(
            db=self.session,
            user_id=self.user_id,
        )

        self.assertEqual(restocked_items, 1)
        self.assertEqual(self.machine_product().quantity, 50)
        self.assertEqual(self.product().quantity, 50)
        self.assertIsNotNone(self.machine_product().last_restocked_at)

    def test_clear_transactions_only_deletes_current_user_records(self):
        self.purchase(quantity=1, budget="10.00")

        other_user = User(
            username="other-purchase-user",
            hashed_password="not-used",
        )
        self.session.add(other_user)
        self.session.flush()
        self.session.add(
            Transaction(
                user_id=other_user.id,
                machine_id=self.machine_id,
                product_id=self.product_id,
                customer_id="OTHER-CUSTOMER",
                quantity=1,
                unit_price=Decimal("3.50"),
                total_price=Decimal("3.50"),
                status=TransactionStatus.SUCCESS,
            )
        )
        self.session.commit()

        result = clear_transactions(
            db=self.session,
            user={"id": self.user_id},
        )

        remaining_transactions = self.session.query(Transaction).all()
        self.assertEqual(result["deleted_count"], 1)
        self.assertEqual(len(remaining_transactions), 1)
        self.assertEqual(remaining_transactions[0].user_id, other_user.id)


if __name__ == "__main__":
    unittest.main()
