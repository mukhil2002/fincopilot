from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
import math

from backend.database import get_db, Transaction
from backend.auth import get_current_user
from backend.models.transaction import TransactionResponse, TransactionListResponse

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])


@router.get("", response_model=TransactionListResponse)
async def get_transactions(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    category: str = Query(default=None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["id"]

    query = db.query(Transaction).filter(
        Transaction.user_id == str(user_id)
    )

    if category:
        query = query.filter(Transaction.category == category)

    total = query.with_entities(func.count()).scalar()
    pages = math.ceil(total / per_page) if total > 0 else 1
    offset = (page - 1) * per_page

    transactions = (
        query.order_by(Transaction.txn_date.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    return TransactionListResponse(
        transactions=transactions,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["id"]

    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == str(user_id),
    ).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return transaction


@router.delete("/{transaction_id}", status_code=204)
async def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["id"]

    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == str(user_id),
    ).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    db.delete(transaction)
    db.commit()

    return None