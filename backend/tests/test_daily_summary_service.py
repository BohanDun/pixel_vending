import tempfile
import unittest
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.database import Base
from api.models import (
    DailySummary,
    Machine,
    Product,
    Transaction,
    TransactionStatus,
    User,
)
from api.services.daily_summary_service import (
    DailySummaryService,
    STORE_TIMEZONE,
)


class DailySummaryServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_directory.name) / "test.db"
        engine = create_engine(
            f"sqlite:///{database_path}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=engine)
        self.session = sessionmaker(bind=engine)()

        user = User(username="summary-user", hashed_password="not-used")
        self.session.add(user)
        self.session.flush()
        product = Product(
            user_id=user.id,
            name="Water",
            description="Test",
            quantity=100,
            price=Decimal("2.00"),
        )
        second_product = Product(
            user_id=user.id,
            name="Cookies",
            description="Test",
            quantity=100,
            price=Decimal("3.00"),
        )
        machine = Machine(
            user_id=user.id,
            name="Summary Machine",
            description="Test",
        )
        self.session.add_all([product, second_product, machine])
        self.session.commit()

        self.user_id = user.id
        self.product_id = product.id
        self.second_product_id = second_product.id
        self.machine_id = machine.id

    def tearDown(self):
        self.session.close()
        self.temp_directory.cleanup()

    def utc_noon_for_local_date(self, local_date: date):
        return (
            datetime.combine(
                local_date,
                time(hour=12),
                tzinfo=STORE_TIMEZONE,
            )
            .astimezone(timezone.utc)
            .replace(tzinfo=None)
        )

    def add_transaction(
        self,
        local_date,
        product_id,
        quantity,
        total_price,
        status,
    ):
        self.session.add(
            Transaction(
                user_id=self.user_id,
                machine_id=self.machine_id,
                product_id=product_id,
                customer_id=f"CUST-{product_id}-{quantity}-{status.value}",
                quantity=quantity,
                unit_price=Decimal("2.00"),
                total_price=Decimal(total_price),
                status=status,
                created_at=self.utc_noon_for_local_date(local_date),
            )
        )

    def test_settle_date_creates_revenue_and_sales_summary(self):
        summary_date = date(2026, 7, 26)
        self.add_transaction(
            summary_date,
            self.product_id,
            2,
            "4.00",
            TransactionStatus.SUCCESS,
        )
        self.add_transaction(
            summary_date,
            self.product_id,
            3,
            "6.00",
            TransactionStatus.SUCCESS,
        )
        self.add_transaction(
            summary_date,
            self.second_product_id,
            1,
            "3.00",
            TransactionStatus.INSUFFICIENT_BUDGET,
        )
        self.session.commit()

        settled = DailySummaryService.settle_date(
            self.session,
            summary_date,
        )

        summary = self.session.query(DailySummary).one()
        self.assertEqual(settled, 1)
        self.assertEqual(summary.total_revenue, Decimal("10.00"))
        self.assertEqual(summary.successful_transactions, 2)
        self.assertEqual(summary.failed_transactions, 1)
        self.assertEqual(summary.units_sold, 5)
        self.assertEqual(summary.top_product_id, self.product_id)

    def test_cleanup_keeps_seven_days_of_transactions_and_thirty_summaries(self):
        today = date(2026, 7, 27)
        old_transaction_date = today - timedelta(days=8)
        recent_transaction_date = today - timedelta(days=2)
        self.add_transaction(
            old_transaction_date,
            self.product_id,
            1,
            "2.00",
            TransactionStatus.SUCCESS,
        )
        self.add_transaction(
            recent_transaction_date,
            self.product_id,
            1,
            "2.00",
            TransactionStatus.SUCCESS,
        )
        self.session.add_all(
            [
                DailySummary(
                    user_id=self.user_id,
                    summary_date=today - timedelta(days=31),
                    total_revenue=Decimal("2.00"),
                    successful_transactions=1,
                    failed_transactions=0,
                    units_sold=1,
                ),
                DailySummary(
                    user_id=self.user_id,
                    summary_date=today - timedelta(days=2),
                    total_revenue=Decimal("2.00"),
                    successful_transactions=1,
                    failed_transactions=0,
                    units_sold=1,
                ),
            ]
        )
        self.session.commit()

        deleted = DailySummaryService.cleanup_old_data(
            self.session,
            today,
        )

        self.assertEqual(deleted["deleted_transactions"], 1)
        self.assertEqual(deleted["deleted_summaries"], 1)
        self.assertEqual(self.session.query(Transaction).count(), 1)
        self.assertEqual(self.session.query(DailySummary).count(), 1)


if __name__ == "__main__":
    unittest.main()
