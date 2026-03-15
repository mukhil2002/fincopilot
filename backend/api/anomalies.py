import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db, Transaction
from backend.auth import get_current_user
from backend.services.anomaly import detect_anomalies

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/anomalies/detect")
def run_anomaly_detection(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Runs all 3 detection methods on this user's transactions.
    Updates is_anomaly and anomaly_reason in the database.
    """
    user_id = current_user["id"]
    logger.info(f"Anomaly detection requested by user {user_id}")

    result = detect_anomalies(db, user_id)
    return result


@router.get("/api/anomalies")
def get_anomalies(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns all transactions flagged as anomalies for this user.
    """
    user_id = current_user["id"]

    anomalies = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.is_anomaly == True
    ).order_by(Transaction.txn_date.desc()).all()

    return {
        "count": len(anomalies),
        "anomalies": [
            {
                "id": t.id,
                "txn_date": t.txn_date,
                "description": t.description,
                "amount": float(t.amount),
                "category": t.category,
                "anomaly_reason": t.anomaly_reason
            }
            for t in anomalies
        ]
    }


@router.patch("/api/anomalies/{transaction_id}/dismiss")
def dismiss_anomaly(
    transaction_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Marks a flagged transaction as reviewed and clears the anomaly flag.
    User is saying: 'I have seen this, it is fine.'
    """
    user_id = current_user["id"]

    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == user_id
    ).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if not transaction.is_anomaly:
        raise HTTPException(status_code=400, detail="Transaction is not flagged as an anomaly")

    transaction.is_anomaly = False
    transaction.anomaly_reason = None
    db.commit()

    logger.info(f"Anomaly dismissed — transaction {transaction_id} by user {user_id}")

    return {"message": "Anomaly dismissed", "transaction_id": transaction_id}