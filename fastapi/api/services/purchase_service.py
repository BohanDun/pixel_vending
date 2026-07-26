from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import joinedload

from api.models import (
    Machine,
    MachineProduct,
    Transaction,
    TransactionStatus,
)
from api.schemas.transaction import PurchaseRequest


class PurchaseService:
    @staticmethod
    def purchase(
        db,
        user_id: int,
        machine_id: int,
        product_id: int,
        payload: PurchaseRequest,
    ) -> Transaction:
        machine = (
            db.query(Machine)
            .filter(Machine.id == machine_id, Machine.user_id == user_id)
            .first()
        )
        if machine is None:
            raise ValueError("Machine not found")

        machine_product = (
            db.query(MachineProduct)
            .options(joinedload(MachineProduct.product))
            .filter(
                MachineProduct.machine_id == machine_id,
                MachineProduct.product_id == product_id,
            )
            .with_for_update()
            .first()
        )

        if machine_product is None or machine_product.product is None:
            return PurchaseService._save_failed_transaction(
                db=db,
                user_id=user_id,
                machine_id=machine_id,
                product_id=None,
                payload=payload,
                status=TransactionStatus.INVALID_PRODUCT,
                reason="Product not found in machine",
            )

        product = machine_product.product
        unit_price = Decimal(product.price)
        total_price = unit_price * payload.quantity

        if machine_product.quantity < payload.quantity:
            return PurchaseService._save_failed_transaction(
                db=db,
                user_id=user_id,
                machine_id=machine_id,
                product_id=product.id,
                payload=payload,
                status=TransactionStatus.OUT_OF_STOCK,
                reason="Not enough machine stock",
                unit_price=unit_price,
                total_price=total_price,
            )

        if payload.budget < total_price:
            return PurchaseService._save_failed_transaction(
                db=db,
                user_id=user_id,
                machine_id=machine_id,
                product_id=product.id,
                payload=payload,
                status=TransactionStatus.INSUFFICIENT_BUDGET,
                reason="Customer budget is insufficient",
                unit_price=unit_price,
                total_price=total_price,
            )

        transaction = Transaction(
            user_id=user_id,
            machine_id=machine_id,
            product_id=product.id,
            customer_id=payload.customer_id,
            quantity=payload.quantity,
            unit_price=unit_price,
            total_price=total_price,
            status=TransactionStatus.SUCCESS,
        )

        try:
            machine_product.quantity -= payload.quantity
            db.add(transaction)
            db.commit()
            db.refresh(transaction)
            return transaction
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def _save_failed_transaction(
        db,
        user_id: int,
        machine_id: int,
        product_id: Optional[int],
        payload: PurchaseRequest,
        status: TransactionStatus,
        reason: str,
        unit_price: Optional[Decimal] = None,
        total_price: Optional[Decimal] = None,
    ) -> Transaction:
        transaction = Transaction(
            user_id=user_id,
            machine_id=machine_id,
            product_id=product_id,
            customer_id=payload.customer_id,
            quantity=payload.quantity,
            unit_price=unit_price,
            total_price=total_price,
            status=status,
            failure_reason=reason,
        )

        try:
            db.add(transaction)
            db.commit()
            db.refresh(transaction)
            return transaction
        except Exception:
            db.rollback()
            raise
