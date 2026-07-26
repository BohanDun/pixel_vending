from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from api.deps import db_dependency, user_dependency
from api.models import Transaction, TransactionStatus
from api.schemas.transaction import PurchaseRequest, TransactionResponse
from api.services import PurchaseService


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
    query = db.query(Transaction).filter(
        Transaction.user_id == user.get("id")
    )
    if transaction_status is not None:
        query = query.filter(Transaction.status == transaction_status)

    return (
        query.order_by(Transaction.created_at.desc(), Transaction.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
