from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DailySummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    summary_date: date
    total_revenue: Decimal
    successful_transactions: int
    failed_transactions: int
    units_sold: int
    top_product_id: Optional[int]
    created_at: datetime
