import logging
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from backend.database import get_db
from backend.auth import get_current_user
from backend.services.summary import generate_summary

logger = logging.getLogger(__name__)

router = APIRouter()


# ── REQUEST MODEL ─────────────────────────────────────────────────────────
# Defines exactly what JSON the frontend must send
# FastAPI validates this automatically — wrong types = 422 error
# ─────────────────────────────────────────────────────────────────────────

class SummaryRequest(BaseModel):
    """
    What the frontend sends:
    {
        "start_date": "2026-03-01",
        "end_date": "2026-03-31"
    }

    Why Pydantic BaseModel?
    FastAPI reads the request body and automatically converts
    "2026-03-01" (a string) into a Python date object.
    If the format is wrong, FastAPI returns a clear 422 error
    before your code even runs.
    """
    start_date: date
    end_date: date


# ── ENDPOINT ──────────────────────────────────────────────────────────────

@router.post("/api/summary")
async def get_summary(
    request: SummaryRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generates a plain-English financial summary for a date range.

    Protected — requires valid JWT token.

    Returns:
    {
        "summary": "March was a solid month for your business...",
        "data": {
            "total_revenue": 12400.00,
            "total_expenses": 8750.00,
            "profit": 3650.00,
            "transaction_count": 47,
            "anomaly_count": 2,
            "top_categories": [["Payroll", 4200.00], ...]
        }
    }
    """

    # Basic date validation — end must be after start
    # Pydantic handles type validation, but logic like this
    # we check ourselves
    if request.end_date < request.start_date:
        raise HTTPException(
            status_code=400,
            detail="end_date must be on or after start_date"
        )

    user_id = current_user["id"]

    result = await generate_summary(
        db=db,
        user_id=user_id,
        start_date=request.start_date,
        end_date=request.end_date
    )

    return result