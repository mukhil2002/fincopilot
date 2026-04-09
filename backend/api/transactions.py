from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
import math
from datetime import date

from backend.database import get_db, Transaction
from backend.auth import get_current_user
from backend.models.transaction import TransactionResponse, TransactionListResponse

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])


@router.get("", response_model=TransactionListResponse)
async def get_transactions(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    category: str = Query(default=None),
    month: str = Query(default=None), 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["id"]

    query = db.query(Transaction).filter(
        Transaction.user_id == str(user_id)
    )

    # AFTER — add month filter below category filter
    if category:
        query = query.filter(Transaction.category == category)

    if month:
        # month = "2026-03" → we need all days in that month
        # e.g. start = 2026-03-01, end = 2026-03-31
        year, mon = int(month.split('-')[0]), int(month.split('-')[1])
        # date(year, month, 1) = first day of that month
        start = date(year, mon, 1)
        # We go to the first day of the NEXT month, then filter < that date
        # This cleanly handles months with 28/29/30/31 days automatically
        if mon == 12:
            end = date(year + 1, 1, 1)   # December → January next year
        else:
            end = date(year, mon + 1, 1)  # Any other month → next month
        query = query.filter(
            Transaction.txn_date >= start,
            Transaction.txn_date < end,
        )

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