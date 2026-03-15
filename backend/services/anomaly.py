import logging
import numpy as np
from scipy import stats
from sklearn.ensemble import IsolationForest
from sqlalchemy.orm import Session
from backend.database import Transaction

logger = logging.getLogger(__name__)


def detect_anomalies(db: Session, user_id: str) -> dict:
    """
    Runs 3 anomaly detection methods on a user's transactions:
    1. Isolation Forest — statistical outliers across all features
    2. Z-score — amount outliers within each category
    3. Rule engine — hard rules: large amounts, missing descriptions, duplicates
    Updates is_anomaly and anomaly_reason on each transaction in the DB.
    """

    # --- Fetch all transactions for this user ---
    transactions = db.query(Transaction).filter(
        Transaction.user_id == user_id
    ).all()

    if len(transactions) < 5:
        return {
            "flagged": 0,
            "total": len(transactions),
            "message": "Not enough data to run detection"
        }

    # --- Extract numeric features for ML ---
    amounts = np.array([float(t.amount) for t in transactions])
    days = np.array([t.txn_date.day for t in transactions])

    # --- Isolation Forest ---
    features = np.column_stack([amounts, days])
    iso_forest = IsolationForest(contamination=0.05, random_state=42)
    iso_predictions = iso_forest.fit_predict(features)

    # --- Z-score per category ---
    flagged_ids = set()
    reasons = {}

    category_groups = {}
    for t in transactions:
        cat = t.category or "Other"
        category_groups.setdefault(cat, []).append(t)

    for cat, group in category_groups.items():
        if len(group) < 3:
            continue
        cat_amounts = np.array([float(t.amount) for t in group])
        z_scores = np.abs(stats.zscore(cat_amounts))
        for i, t in enumerate(group):
            if z_scores[i] > 3.0:
                flagged_ids.add(t.id)
                reasons[t.id] = f"Large amount outlier in '{cat}' (Z-score: {z_scores[i]:.1f})"

    # --- Add Isolation Forest flags ---
    for i, t in enumerate(transactions):
        if iso_predictions[i] == -1:
            flagged_ids.add(t.id)
            if t.id not in reasons:
                reasons[t.id] = "Statistical outlier (Isolation Forest)"

    # --- Rule engine ---
    seen = {}
    for t in transactions:
        # Rule 1: Large absolute amount
        if abs(float(t.amount)) > 5000:
            flagged_ids.add(t.id)
            reasons[t.id] = f"Large transaction: £{abs(float(t.amount)):,.2f}"

        # Rule 2: Empty or very short description
        if not t.description or len(t.description.strip()) < 3:
            flagged_ids.add(t.id)
            reasons[t.id] = "Missing or incomplete description"

        # Rule 3: Duplicate detection
        key = (t.description.strip().lower(), float(t.amount))
        if key in seen:
            prev = seen[key]
            days_apart = abs((t.txn_date - prev.txn_date).days)
            if days_apart <= 7:
                flagged_ids.add(t.id)
                flagged_ids.add(prev.id)
                reasons[t.id] = f"Possible duplicate of transaction on {prev.txn_date}"
                reasons[prev.id] = f"Possible duplicate of transaction on {t.txn_date}"
        seen[key] = t

    # --- Write results to database ---
    flagged_count = 0
    for t in transactions:
        if t.id in flagged_ids:
            t.is_anomaly = True
            t.anomaly_reason = reasons.get(t.id, "Anomaly detected")
            flagged_count += 1
        else:
            t.is_anomaly = False
            t.anomaly_reason = None

    db.commit()

    logger.info(
        f"Anomaly detection complete — {flagged_count}/{len(transactions)} flagged for user {user_id}"
    )

    return {
        "flagged": flagged_count,
        "total": len(transactions),
        "message": f"Detection complete. {flagged_count} transaction(s) flagged."
    }