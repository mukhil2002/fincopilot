import logging
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from backend.database import get_db
from backend.auth import get_current_user
from backend.services.qa import answer_question

logger = logging.getLogger(__name__)

router = APIRouter()


# ── REQUEST MODEL ─────────────────────────────────────────────────────────

class QARequest(BaseModel):
    """
    What the frontend sends:
    {
        "question": "What is my biggest expense category?",
        "start_date": "2026-03-01",   ← optional
        "end_date": "2026-03-31"       ← optional
    }

    Why Optional[date] with None default?
    Dates are not required for Q&A. If the user just asks a question
    without filtering by date, we search all their transactions.
    Pydantic handles the None case automatically.
    """
    question: str
    start_date: date | None = None
    end_date: date | None = None


# ── ENDPOINT ──────────────────────────────────────────────────────────────

@router.post("/api/qa")
async def qa(
    request: QARequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Answers a natural language question about the user's finances.

    Protected — requires valid JWT token.

    Returns:
    {
        "answer": "Your biggest expense is Payroll at £4,200...",
        "transaction_count": 47
    }
    """

    # Don't allow empty questions
    if not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty"
        )

    # If one date is provided, both must be provided
    # A start with no end (or vice versa) is ambiguous
    if bool(request.start_date) != bool(request.end_date):
        raise HTTPException(
            status_code=400,
            detail="Provide both start_date and end_date, or neither"
        )

    # If both dates provided, end must be after start
    if request.start_date and request.end_date:
        if request.end_date < request.start_date:
            raise HTTPException(
                status_code=400,
                detail="end_date must be on or after start_date"
            )

    user_id = current_user["id"]

    result = await answer_question(
        db=db,
        user_id=user_id,
        question=request.question,
        start_date=request.start_date,
        end_date=request.end_date
    )

    return result