import enum

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.sql import func

from ..database import Base


class TransactionStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    INSUFFICIENT_BUDGET = "INSUFFICIENT_BUDGET"
    INVALID_PRODUCT = "INVALID_PRODUCT"
    FAILED = "FAILED"


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_user_created", "user_id", "created_at"),
        Index(
            "ix_transactions_user_status_created",
            "user_id",
            "status",
            "created_at",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    machine_id = Column(
        Integer,
        ForeignKey("machines.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    customer_id = Column(String, nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=True)
    total_price = Column(Numeric(10, 2), nullable=True)
    status = Column(
        Enum(
            TransactionStatus,
            name="transaction_status",
            native_enum=False,
        ),
        nullable=False,
        index=True,
    )
    failure_reason = Column(String, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
