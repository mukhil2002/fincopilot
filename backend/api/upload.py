import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from backend.database import get_db, Upload, Transaction
from backend.auth import get_current_user
from backend.services.parser import parse_csv
from backend.services.corrections import apply_corrections
from backend.services.categoriser import categorise_transactions
from backend.models.upload import UploadResponse, UploadHistoryItem, UploadHistoryResponse

router = APIRouter(prefix="/api", tags=["Upload"])


# ── HELPER ───────────────────────────────────────────────────────────────
# Deduplication Layer 2 — transaction level
# Checks if a single transaction already exists for this user
# Match = same date + same description + same amount
# ─────────────────────────────────────────────────────────────────────────

def transaction_exists(
    db: Session,
    user_id: str,
    date: str,
    description: str,
    amount: float
) -> bool:
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
# Full pipeline: validate → parse → dedup → corrections → categorise → save
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
    3. Layer 1 dedup: reject if exact file uploaded before
    4. Layer 2 dedup: skip individual transactions already in DB
    5. Correction lookup: apply saved user corrections before Claude
    6. Claude categorisation: categorise remaining transactions
    7. Save upload record + all transactions to DB
    8. Return counts
    """
    user_id = current_user["id"]

    # ── STEP 1: VALIDATION ───────────────────────────────────────────────
    # Check file is a CSV
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported. Please upload a .csv file."
        )

    # Read the raw bytes of the file into memory once and reuse
    file_bytes = await file.read()

    # 10MB = 10 * 1024 * 1024 bytes
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

    # ── STEP 2: PARSE ────────────────────────────────────────────────────
    # parser.py handles encoding detection, column auto-detection,
    # date normalisation, amount cleaning
    try:
        parsed = parse_csv(file_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    file_hash = parsed["file_hash"]
    raw_transactions = parsed["transactions"]
    skipped_rows = parsed["skipped_rows"]

    # ── STEP 3: LAYER 1 DEDUP (file level) ──────────────────────────────
    # Same MD5 hash + same user = exact same file uploaded before
    existing_upload = db.query(Upload).filter(
        Upload.user_id == user_id,
        Upload.file_hash == file_hash
    ).first()

    if existing_upload:
        raise HTTPException(
            status_code=400,
            detail=f"This file was already uploaded on {existing_upload.uploaded_at.strftime('%d %b %Y')}. No duplicates added."
        )

    # ── STEP 4: LAYER 2 DEDUP (transaction level) ────────────────────────
    # Even if the file is new, individual transactions may already exist
    # e.g. user uploads two CSVs with overlapping date ranges
    new_transactions = []
    duplicate_count = 0

    for txn in raw_transactions:
        if transaction_exists(db, user_id, txn["date"], txn["description"], txn["amount"]):
            duplicate_count += 1
        else:
            new_transactions.append(txn)

    # If every transaction was a duplicate, save the upload record and stop
    # We still save it so the user can see the attempt in their history
    if not new_transactions:
        upload_id = str(uuid.uuid4())
        upload_record = Upload(
            id=upload_id,
            user_id=user_id,
            filename=file.filename,
            file_hash=file_hash,
            uploaded_at=datetime.now(timezone.utc),
            new_count=0,
            duplicate_count=duplicate_count,
            status="completed"
        )
        db.add(upload_record)
        db.commit()

        return UploadResponse(
            upload_id=upload_id,
            filename=file.filename,
            new_count=0,
            duplicate_count=duplicate_count,
            skipped_rows=skipped_rows,
            anomalies_found=0,
            message=f"No new transactions. All {duplicate_count} transactions already exist.",
            uploaded_at=datetime.now(timezone.utc)
        )

    # ── STEP 5: CORRECTION LOOKUP ────────────────────────────────────────
    # Before calling Claude, check if the user has already corrected
    # transactions like these before.
    #
    # Example: user previously corrected "TESCO" → "Personal / Drawings"
    # Any new transaction whose description contains "TESCO" gets that
    # category applied directly. Confidence = 1.0. Claude not called.
    #
    # corrected  = transactions with a saved correction applied
    # for_claude = transactions with no saved correction → go to Claude
    corrected, for_claude = apply_corrections(new_transactions, user_id, db)

    # ── STEP 6: CLAUDE CATEGORISATION ────────────────────────────────────
    # Send only the transactions that had no saved correction.
    # categorise_transactions() returns the same list with category,
    # confidence, and note fields added to each transaction dict.
    if for_claude:
        categorised = await categorise_transactions(for_claude)
    else:
        # Every transaction was handled by corrections — Claude not needed
        categorised = []

    # Merge both lists — all transactions now have category + confidence
    all_categorised = corrected + categorised

    # ── STEP 7: SAVE TO DATABASE ─────────────────────────────────────────
    # Save the upload record first (so we have an upload_id),
    # then save each transaction linked to that upload_id.
    # Wrapped in try/except — if anything fails, rollback everything.
    # Either all transactions save or none do. Never partial data.
    upload_id = str(uuid.uuid4())

    try:
        # Save upload record
        upload_record = Upload(
            id=upload_id,
            user_id=user_id,
            filename=file.filename,
            file_hash=file_hash,
            uploaded_at=datetime.now(timezone.utc),
            new_count=len(all_categorised),
            duplicate_count=duplicate_count,
            status="completed"
        )
        db.add(upload_record)
        db.flush()
        # flush() sends the INSERT without committing
        # upload_id is now available for transactions to reference
        # but we can still rollback if something goes wrong below

        # Save each transaction with its real category
        for txn in all_categorised:
            transaction_record = Transaction(
                user_id=user_id,
                upload_id=upload_id,
                txn_date=txn["date"],
                description=txn["description"],
                amount=txn["amount"],
                currency="GBP",
                # These three lines are what changed from Day 4
                # Before: category="Uncategorised", confidence=0.0
                # Now: real values from Claude or corrections table
                category=txn.get("category", "Other"),
                confidence=txn.get("confidence", 0.5),
                is_anomaly=False,
                # correction_applied=True means user already confirmed this
                # category previously — so manually_corrected = True
                manually_corrected=txn.get("correction_applied", False),
                created_at=datetime.now(timezone.utc)
            )
            db.add(transaction_record)

        # Commit everything at once
        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save upload: {str(e)}"
        )

    # ── STEP 8: RESPONSE ─────────────────────────────────────────────────
    new_count = len(all_categorised)

    if new_count == 0:
        message = f"No new transactions. All {duplicate_count} transactions already exist."
    elif duplicate_count == 0:
        message = f"{new_count} new transactions added and categorised successfully."
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