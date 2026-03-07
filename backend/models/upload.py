from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class UploadResponse(BaseModel):
    """
    Shape of the response returned to React after a CSV upload.
    
    Every field here is what the frontend will receive and display.
    For example:
        new_count       → "16 new transactions added"
        duplicate_count → "3 duplicates skipped"
        anomalies_found → badge count on the dashboard
    """
    upload_id: str
    filename: str
    new_count: int
    duplicate_count: int
    skipped_rows: int
    anomalies_found: int
    message: str
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class UploadHistoryItem(BaseModel):
    """
    Shape of a single item in the upload history list.
    Used by GET /api/uploads to show the user their past uploads.
    """
    id: str
    filename: str
    new_count: int
    duplicate_count: int
    status: str
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class UploadHistoryResponse(BaseModel):
    """
    Wraps the list of past uploads with a total count.
    """
    uploads: list[UploadHistoryItem]
    total: int