from typing import List

from fastapi import APIRouter, Query

from api.deps import db_dependency, user_dependency
from api.models import DailySummary
from api.schemas.daily_summary import DailySummaryResponse


router = APIRouter(prefix="/daily-summaries", tags=["daily summaries"])


@router.get("/", response_model=List[DailySummaryResponse])
def get_daily_summaries(
    db: db_dependency,
    user: user_dependency,
    limit: int = Query(default=30, ge=1, le=30),
):
    return (
        db.query(DailySummary)
        .filter(DailySummary.user_id == user.get("id"))
        .order_by(DailySummary.summary_date.desc())
        .limit(limit)
        .all()
    )
