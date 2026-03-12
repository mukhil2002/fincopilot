import logging
from sqlalchemy.orm import Session
from backend.database import Correction

logger = logging.getLogger(__name__)


def apply_corrections(
    transactions: list[dict],
    user_id: str,
    db: Session
) -> tuple[list[dict], list[dict]]:
    """
    Checks each transaction against the user's saved corrections.

    For each transaction:
    - If its description CONTAINS a saved pattern → apply that category
      directly. Set confidence to 1.0. Mark as correction_applied = True.
    - If no pattern matches → leave it for Claude.

    Returns two separate lists:
        corrected   → transactions that matched a saved correction
        for_claude  → transactions that need Claude to categorise

    Why separate lists?
    The upload pipeline needs to know which transactions to send to Claude
    and which to skip. Keeping them separate makes that logic clean.

    Example:
        Saved correction: description_pattern="TESCO", correct_category="Personal / Drawings"
        Transaction:      description="TESCO METRO LONDON", amount=-4.50

        "TESCO" in "TESCO METRO LONDON".upper() → True
        → category = "Personal / Drawings", confidence = 1.0
        → goes into corrected list, NOT sent to Claude
    """

    # Load all corrections for this user in one DB query
    # We do this once up front — much more efficient than
    # querying the DB once per transaction
    saved_corrections = db.query(Correction).filter(
        Correction.user_id == user_id
    ).all()

    # If this user has no corrections yet, skip all the logic
    # All transactions go straight to Claude
    if not saved_corrections:
        return [], transactions

    corrected = []
    for_claude = []

    for transaction in transactions:
        description_upper = transaction["description"].upper()
        matched = False

        for correction in saved_corrections:
            pattern_upper = correction.description_pattern.upper()

            # Check if the saved pattern appears anywhere in the description
            # We use .upper() on both sides so matching is case-insensitive
            # "tesco" matches "TESCO METRO LONDON"
            # "AMAZON" matches "Amazon Prime Monthly"
            if pattern_upper in description_upper:
                transaction["category"] = correction.correct_category
                transaction["confidence"] = 1.0
                transaction["note"] = "Category confirmed by you previously"
                transaction["correction_applied"] = True

                logger.info(
                    f"Correction applied: '{transaction['description']}' "
                    f"→ '{correction.correct_category}' (pattern: '{correction.description_pattern}')"
                )

                corrected.append(transaction)
                matched = True
                break  # Stop checking other patterns — first match wins

        if not matched:
            for_claude.append(transaction)

    logger.info(
        f"Corrections: {len(corrected)} applied from saved rules, "
        f"{len(for_claude)} sent to Claude"
    )

    return corrected, for_claude