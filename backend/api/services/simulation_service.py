import random

from sqlalchemy.orm import joinedload

from api.models import Machine, MachineProduct
from api.schemas.transaction import PurchaseRequest
from api.services.customer_generator import CustomerGenerator
from api.services.purchase_service import PurchaseService


class SimulationService:
    def __init__(self, randomizer=None):
        self.randomizer = randomizer or random.Random()
        self.customer_generator = CustomerGenerator(self.randomizer)

    def run_once(self, db, user_id: int):
        machines = (
            db.query(Machine)
            .options(
                joinedload(Machine.machine_products).joinedload(
                    MachineProduct.product
                )
            )
            .filter(Machine.user_id == user_id)
            .all()
        )
        if not machines:
            raise ValueError("No machine is available")

        available_machines = [
            (
                machine,
                [
                    machine_product
                    for machine_product in machine.machine_products
                    if machine_product.product is not None
                ],
            )
            for machine in machines
            if any(
                machine_product.product is not None
                for machine_product in machine.machine_products
            )
        ]
        if not available_machines:
            raise ValueError("No product is available for simulation")

        machine_count = self.randomizer.randint(
            1,
            min(3, len(available_machines)),
        )
        selected_machines = self.randomizer.sample(
            available_machines,
            machine_count,
        )
        customer = self.customer_generator.generate()
        remaining_budget = customer.budget
        purchases = []

        for machine, stocked_products in selected_machines:
            product_type_count = self.randomizer.randint(
                1,
                min(3, len(stocked_products)),
            )
            selected_products = self.randomizer.sample(
                stocked_products,
                product_type_count,
            )

            for machine_product in selected_products:
                quantity = self.randomizer.randint(1, 3)
                product_name = machine_product.product.name
                transaction = PurchaseService.purchase(
                    db=db,
                    user_id=user_id,
                    machine_id=machine.id,
                    product_id=machine_product.product_id,
                    payload=PurchaseRequest(
                        customer_id=customer.customer_id,
                        quantity=quantity,
                        budget=remaining_budget,
                    ),
                )
                if transaction.status.value == "SUCCESS":
                    remaining_budget -= transaction.total_price

                purchases.append(
                    {
                        "machine_id": machine.id,
                        "machine_name": machine.name,
                        "product_id": machine_product.product_id,
                        "product_name": product_name,
                        "quantity": quantity,
                        "transaction": transaction,
                    }
                )

        return {
            "customer": customer,
            "purchases": purchases,
        }
