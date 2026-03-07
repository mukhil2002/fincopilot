from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
import uuid


class TransactionResponse(BaseModel):
    id: int
    user_id: uuid.UUID
    upload_id: Optional[uuid.UUID] = None
    txn_date: date
    description: str
    amount: Decimal
    currency: str
    category: Optional[str] = None
    confidence: Optional[Decimal] = None
    is_anomaly: bool
    anomaly_reason: Optional[str] = None
    manually_corrected: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionListResponse(BaseModel):
    transactions: list[TransactionResponse]
    total: int
    page: int
    per_page: int
    pages: int