from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, condecimal


class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    quantity: int = Field(ge=0)
    price: condecimal(max_digits=10, decimal_places=2, ge=Decimal("0.00"))


class ProductCreate(ProductBase):
    pass


class ProductPriceUpdate(BaseModel):
    price: condecimal(max_digits=10, decimal_places=2, ge=Decimal("0.00"))


class ProductQuantityChange(BaseModel):
    quantity: int = Field(gt=0)
