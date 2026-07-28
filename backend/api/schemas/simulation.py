from decimal import Decimal
from typing import List

from pydantic import BaseModel

from api.schemas.transaction import TransactionResponse


class SpriteAppearance(BaseModel):
    skin: str
    hair: str
    shirt: str
    pants: str
    accessory: str


class VirtualCustomer(BaseModel):
    customer_id: str
    name: str
    sprite: SpriteAppearance
    budget: Decimal


class SimulationPurchaseResponse(BaseModel):
    machine_id: int
    machine_name: str
    product_id: int
    product_name: str
    quantity: int
    transaction: TransactionResponse


class SimulationRunResponse(BaseModel):
    customer: VirtualCustomer
    purchases: List[SimulationPurchaseResponse]
