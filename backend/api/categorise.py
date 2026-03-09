import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from backend.auth import get_current_user
from backend.services.categoriser import categorise_transactions

logger = logging.getLogger(__name__)

router = APIRouter()


class TransactionInput(BaseModel):
    description: str
    amount: float


class CategoriseRequest(BaseModel):
    transactions: list[TransactionInput]


@router.post("/api/categorise")
async def categorise_endpoint(
    request: CategoriseRequest,
    current_user: dict = Depends(get_current_user)
):
    logger.info(f"Categorise request for {len(request.transactions)} transactions")

    transactions_as_dicts = [
        {"description": t.description, "amount": t.amount}
        for t in request.transactions
    ]

    results = await categorise_transactions(transactions_as_dicts)

    return {
        "count": len(results),
        "transactions": results
    }