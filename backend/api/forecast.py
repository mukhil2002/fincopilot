import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.auth import get_current_user
from backend.services.forecast import generate_forecast

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["forecast"])


@router.get("/forecast")
async def get_forecast(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logger.info(f"Forecast requested by user {current_user['id']}")

    result = await generate_forecast(
        db=db,
        user_id=current_user["id"]
    )

    return result