import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from backend.database import get_db, Upload, Transaction
from backend.auth import get_current_user
from backend.services.parser import parse_csv
from backend.models.upload import UploadResponse, UploadHistoryItem, UploadHistoryResponse

router = APIRouter(prefix="/api", tags=["Upload"])


# ── HELPER ───────────────────────────────────────────────────────────────
# Deduplication Layer 2 — transaction level
# Checks if a single transaction already exists for this user
# Match = same date + same description + same amount
# ─────────────────────────────────────────────────────────────────────────

def transaction_exists(db: Session, user_id: str, date: str, description: str, amount: float) -> bool:
    """
    Returns True if this exact transaction already exists for this user.
    
    We match on date + description + amount together.
    Any one field different = treat as a new transaction.
    All three match = duplicate, skip it.
    """
    existing = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.txn_date == date,
        Transaction.description == description,
        Transaction.amount == amount
    ).first()
    
    return existing is not None


# ── ENDPOINT 1 ───────────────────────────────────────────────────────────
# POST /api/upload
# Accepts a CSV file, runs the full pipeline, saves to DB
# ─────────────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Main upload endpoint. Full pipeline:
    1. Validate file type and size
    2. Parse CSV → clean transactions + file hash
    3. Layer 1 dedup: check if this exact file was uploaded before
    4. Layer 2 dedup: check each transaction individually
    5. Save upload record + new transactions to DB
    6. Return counts
    """
    user_id = current_user["id"]

    # ── VALIDATION ───────────────────────────────────────────────────────
    # Check file is a CSV
    # UploadFile.filename is the original filename from the user's computer
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported. Please upload a .csv file."
        )
    
    # Read the raw bytes of the file into memory
    # We do this once and reuse — avoids reading the file multiple times
    file_bytes = await file.read()
    
    # Check file size — 10MB max
    # len(file_bytes) gives us the size in bytes
    # 10MB = 10 * 1024 * 1024 bytes = 10,485,760 bytes
    max_size = 10 * 1024 * 1024
    if len(file_bytes) > max_size:
        raise HTTPException(
            status_code=400,
            detail="File is too large. Maximum size is 10MB."
        )
    
    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=400,
            detail="File is empty."
        )

    # ── PARSE ────────────────────────────────────────────────────────────
    # Call our parser service — returns file_hash + clean transactions
    try:
        parsed = parse_csv(file_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    file_hash = parsed["file_hash"]
    raw_transactions = parsed["transactions"]
    skipped_rows = parsed["skipped_rows"]

    # ── LAYER 1 DEDUP ────────────────────────────────────────────────────
    # Check if this exact file has been uploaded before by this user
    # Same file = same MD5 hash
    existing_upload = db.query(Upload).filter(
        Upload.user_id == user_id,
        Upload.file_hash == file_hash
    ).first()
    
    if existing_upload:
        raise HTTPException(
            status_code=400,
            detail=f"This file was already uploaded on {existing_upload.uploaded_at.strftime('%d %b %Y')}. No duplicates added."
        )

    # ── LAYER 2 DEDUP ────────────────────────────────────────────────────
    # Check each transaction individually
    # Even if the file is new, some transactions may already exist
    # (e.g. user uploads overlapping date range from a different file)
    new_transactions = []
    duplicate_count = 0

    for txn in raw_transactions:
        if transaction_exists(db, user_id, txn["date"], txn["description"], txn["amount"]):
            duplicate_count += 1
        else:
            new_transactions.append(txn)

    # ── SAVE TO DATABASE ─────────────────────────────────────────────────
    # Create the upload record first so we have an upload_id
    # Then create each transaction linked to that upload_id
    # 
    # We wrap everything in a try/except so if anything fails,
    # we don't save a partial upload (all or nothing)

    upload_id = str(uuid.uuid4())
    
    try:
        # Save upload record
        upload_record = Upload(
            id=upload_id,
            user_id=user_id,
            filename=file.filename,
            file_hash=file_hash,
            uploaded_at=datetime.now(timezone.utc),
            new_count=len(new_transactions),
            duplicate_count=duplicate_count,
            status="completed"
        )
        db.add(upload_record)
        db.flush()
        # flush() sends the INSERT to the DB but doesn't commit yet
        # This means upload_record.id is now available to use
        # but we can still roll back if something goes wrong

        # Save each new transaction
        for txn in new_transactions:
            transaction_record = Transaction(
                user_id=user_id,
                upload_id=upload_id,
                txn_date=txn["date"],
                description=txn["description"],
                amount=txn["amount"],
                currency="GBP",
                category="Uncategorised",
                confidence=0.0,
                is_anomaly=False,
                manually_corrected=False,
                created_at=datetime.now(timezone.utc)
            )
            db.add(transaction_record)

        # Commit everything at once — all or nothing
        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save upload: {str(e)}"
        )

    # ── RESPONSE ─────────────────────────────────────────────────────────
    new_count = len(new_transactions)
    
    if new_count == 0:
        message = f"No new transactions. All {duplicate_count} transactions already exist."
    elif duplicate_count == 0:
        message = f"{new_count} new transactions added successfully."
    else:
        message = f"{new_count} new transactions added. {duplicate_count} duplicates skipped."

    return UploadResponse(
        upload_id=upload_id,
        filename=file.filename,
        new_count=new_count,
        duplicate_count=duplicate_count,
        skipped_rows=skipped_rows,
        anomalies_found=0,  # Day 8 — anomaly detection wired in here
        message=message,
        uploaded_at=datetime.now(timezone.utc)
    )


# ── ENDPOINT 2 ───────────────────────────────────────────────────────────
# GET /api/uploads
# Returns upload history for this user
# ─────────────────────────────────────────────────────────────────────────

@router.get("/uploads", response_model=UploadHistoryResponse)
async def get_uploads(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Returns all past uploads for this user, newest first.
    """
    user_id = current_user["id"]
    
    uploads = db.query(Upload).filter(
        Upload.user_id == user_id
    ).order_by(Upload.uploaded_at.desc()).all()
    
    return UploadHistoryResponse(
        uploads=[
            UploadHistoryItem(
                id=str(upload.id),
                filename=upload.filename,
                new_count=upload.new_count,
                duplicate_count=upload.duplicate_count,
                status=upload.status,
                uploaded_at=upload.uploaded_at
            )
            for upload in uploads
        ],
        total=len(uploads)
    )


# ── ENDPOINT 3 ───────────────────────────────────────────────────────────
# DELETE /api/uploads/{id}
# Deletes an upload batch and all its transactions
# ─────────────────────────────────────────────────────────────────────────

@router.delete("/uploads/{upload_id}", status_code=204)
async def delete_upload(
    upload_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Deletes an upload and all transactions that came from it.
    
    We delete transactions first, then the upload record.
    This is because transactions have a foreign key pointing to uploads —
    you cannot delete a parent row while child rows still reference it.
    """
    user_id = current_user["id"]
    
    # Find the upload — make sure it belongs to this user
    upload = db.query(Upload).filter(
        Upload.id == upload_id,
        Upload.user_id == user_id
    ).first()
    
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    try:
        # Delete transactions first (children before parent)
        db.query(Transaction).filter(
            Transaction.upload_id == upload_id
        ).delete()
        
        # Now delete the upload record
        db.delete(upload)
        db.commit()
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete upload: {str(e)}")