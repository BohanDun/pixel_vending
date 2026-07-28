from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from api.deps import db_dependency, user_dependency
from api.models import Transaction, TransactionStatus
from api.schemas.transaction import PurchaseRequest, TransactionResponse
from api.services import PurchaseService
from api.services.daily_summary_service import (
    DailySummaryService,
    STORE_TIMEZONE,
    TRANSACTION_RETENTION_DAYS,
)


router = APIRouter(tags=["transactions"])


@router.post(
    "/machines/{machine_id}/products/{product_id}/purchase",
    response_model=TransactionResponse,
)
def purchase_product(
    db: db_dependency,
    user: user_dependency,
    machine_id: int,
    product_id: int,
    payload: PurchaseRequest,
):
    try:
        return PurchaseService.purchase(
            db=db,
            user_id=user.get("id"),
            machine_id=machine_id,
            product_id=product_id,
            payload=payload,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/transactions/", response_model=List[TransactionResponse])
def get_transactions(
    db: db_dependency,
    user: user_dependency,
    transaction_status: Optional[TransactionStatus] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    cutoff_date = datetime.now(STORE_TIMEZONE).date() - timedelta(
        days=TRANSACTION_RETENTION_DAYS
    )
    cutoff_utc, _ = DailySummaryService.utc_bounds_for_local_date(
        cutoff_date
    )
    query = db.query(Transaction).filter(
        Transaction.user_id == user.get("id"),
        Transaction.created_at >= cutoff_utc,
    )
    if transaction_status is not None:
        query = query.filter(Transaction.status == transaction_status)

    return (
        query.order_by(Transaction.created_at.desc(), Transaction.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.delete("/transactions/")
def clear_transactions(db: db_dependency, user: user_dependency):
    deleted_count = (
        db.query(Transaction)
        .filter(Transaction.user_id == user.get("id"))
        .delete(synchronize_session=False)
    )
    db.commit()
    return {"deleted_count": deleted_count}
