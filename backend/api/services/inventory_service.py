from datetime import datetime, timezone

from sqlalchemy.orm import joinedload

from api.models import Machine, MachineProduct
from api.models.machine import DEFAULT_MACHINE_PRODUCT_CAPACITY


class InventoryService:
    @staticmethod
    def restock_all_low_stock(db, user_id: int) -> int:
        low_stock_items = (
            db.query(MachineProduct)
            .join(Machine, Machine.id == MachineProduct.machine_id)
            .options(joinedload(MachineProduct.product))
            .filter(
                Machine.user_id == user_id,
                MachineProduct.auto_restock_enabled.is_(True),
                MachineProduct.quantity <= MachineProduct.low_stock_threshold,
            )
            .all()
        )

        restocked_items = 0
        try:
            for machine_product in low_stock_items:
                if InventoryService.restock_if_needed(machine_product) > 0:
                    restocked_items += 1
            db.commit()
            return restocked_items
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def restock_if_needed(machine_product: MachineProduct) -> int:
        if not machine_product.auto_restock_enabled:
            return 0

        threshold = machine_product.low_stock_threshold
        if threshold is None:
            threshold = 5

        if machine_product.quantity > threshold:
            return 0

        return InventoryService._restock_to_capacity(machine_product)

    @staticmethod
    def restock_after_stockout(machine_product: MachineProduct) -> int:
        if not machine_product.auto_restock_enabled:
            return 0

        return InventoryService._restock_to_capacity(machine_product)

    @staticmethod
    def _restock_to_capacity(machine_product: MachineProduct) -> int:
        capacity = machine_product.capacity
        if capacity is None:
            capacity = DEFAULT_MACHINE_PRODUCT_CAPACITY

        required_to_fill = capacity - machine_product.quantity
        warehouse_stock = machine_product.product.quantity
        if warehouse_stock < required_to_fill:
            warehouse_stock = capacity * 2
            machine_product.product.quantity = warehouse_stock

        quantity_to_add = min(
            required_to_fill,
            warehouse_stock,
        )
        if quantity_to_add <= 0:
            return 0

        machine_product.product.quantity -= quantity_to_add
        machine_product.quantity += quantity_to_add
        machine_product.last_restocked_at = datetime.now(timezone.utc)
        return quantity_to_add
