import logging
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.auth import get_current_user
from backend.services.report import generate_report

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/report", tags=["Report"])


@router.get("/pdf")
async def download_pdf_report(
    month: str = Query(..., description="Month in YYYY-MM format, e.g. 2026-03"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Generates and returns a PDF report for the given month.

    GET /api/report/pdf?month=2026-03

    Why Query(...) with three dots?
    The ... means this parameter is REQUIRED — no default value.
    If the caller doesn't include ?month=..., FastAPI returns a
    clear 422 validation error automatically.

    Why return Response directly instead of a dict?
    Every other endpoint returns JSON (a dict).
    This endpoint returns raw PDF bytes.
    FastAPI's Response class lets us send any raw bytes with
    any content type — in this case application/pdf.
    The browser sees that content type and triggers a file download.
    """

    # ── 1. Parse and validate the month parameter ──
    try:
        year, mon = int(month.split('-')[0]), int(month.split('-')[1])
    except (ValueError, IndexError):
        raise HTTPException(
            status_code=400,
            detail="month must be in YYYY-MM format, e.g. 2026-03"
        )

    # ── 2. Calculate the date range ──
    # Same logic as transactions.py — first day to last day of month
    start_date = date(year, mon, 1)
    if mon == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, mon + 1, 1)

    # ── 3. Build a human-readable period label ──
    # e.g. "March 2026" — used in the PDF header and filename
    period_label = start_date.strftime("%B %Y")

    # ── 4. Get user info ──
    user_id = current_user["id"]
    user_email = current_user.get("email", "")

    logger.info(f"PDF report requested by {user_email} for {period_label}")

    # ── 5. Generate the PDF ──
    try:
        pdf_bytes = await generate_report(
            db=db,
            user_id=str(user_id),
            user_email=user_email,
            start_date=start_date,
            end_date=end_date,
            period_label=period_label,
        )
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate report")

    # ── 6. Return the PDF as a downloadable file ──
    filename = f"fincopilot-{month}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            # Content-Disposition: attachment tells the browser
            # "save this as a file" rather than trying to display it
            # filename= sets the default filename in the save dialog
            "Content-Disposition": f"attachment; filename={filename}",

            # Content-Length tells the browser exactly how many bytes
            # are coming — allows it to show a progress bar on large files
            "Content-Length": str(len(pdf_bytes)),
        }
    )