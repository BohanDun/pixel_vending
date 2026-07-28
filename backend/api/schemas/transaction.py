from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, condecimal

from api.models.transaction import TransactionStatus


Money = condecimal(max_digits=10, decimal_places=2, ge=Decimal("0.00"))


class PurchaseRequest(BaseModel):
    customer_id: str = Field(min_length=1, max_length=100)
    quantity: int = Field(gt=0)
    budget: Money


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    machine_id: Optional[int]
    product_id: Optional[int]
    customer_id: str
    quantity: int
    unit_price: Optional[Decimal]
    total_price: Optional[Decimal]
    status: TransactionStatus
    failure_reason: Optional[str]
    created_at: datetime
