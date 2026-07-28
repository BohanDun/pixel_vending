from typing import List, Optional

from pydantic import BaseModel, Field


class MachineBase(BaseModel):
    name: str
    description: Optional[str] = None


class MachineCreate(MachineBase):
    products: List[int] = Field(default_factory=list)
    product_names: List[str] = Field(default_factory=list)


class MachineProductQuantity(BaseModel):
    quantity: int = Field(default=0, ge=0)


class MachineProductSettings(BaseModel):
    capacity: int = Field(gt=0)
    low_stock_threshold: int = Field(ge=0)
    auto_restock_enabled: bool
