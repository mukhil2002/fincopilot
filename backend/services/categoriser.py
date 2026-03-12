import json
import asyncio
import logging
from anthropic import Anthropic
from backend.config import TRANSACTION_CATEGORIES, ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

# Create the Anthropic client once at module level
# This is efficient — one client reused for every call
# rather than creating a new one every time
client = Anthropic(api_key=ANTHROPIC_API_KEY)

BATCH_SIZE = 25


# ── STEP 1 ───────────────────────────────────────────────────────────────
# Build the prompt we send to Claude
# We inject the category list and transactions dynamically
# ─────────────────────────────────────────────────────────────────────────

def _build_prompt(transactions: list[dict]) -> str:
    """
    Builds the user message sent to Claude.
    
    We format the 14 categories as a clean bullet list.
    We send transactions as JSON so Claude can parse them reliably.
    
    The _id prefix is intentional — we explain what Claude must return.
    """
    categories_list = "\n".join(f"- {cat}" for cat in TRANSACTION_CATEGORIES)
    transactions_text = json.dumps(transactions, indent=2)

    prompt = f"""You are a professional UK bookkeeper.
Categorise each transaction into EXACTLY one category from this list:

{categories_list}

Rules:
- Return ONLY a valid JSON array. No explanation, no markdown, no extra text.
- Every transaction must have: id, category, confidence, note
- confidence is a float between 0.0 and 1.0
- note is a brief reason for your choice (one sentence)
- If unsure, use "Other"
- Use UK context: HMRC = tax, VAT = VAT Payment, TFL/TRAINLINE = Travel & Transport

Transactions to categorise:
{transactions_text}

Return format:
[{{"id": "0", "category": "Supplies", "confidence": 0.95, "note": "Supermarket purchase"}}]"""

    return prompt


# ── STEP 2 ───────────────────────────────────────────────────────────────
# Validate a single result from Claude
# Claude is AI — it can return invalid categories or bad confidence values
# This function cleans up anything unexpected
# ─────────────────────────────────────────────────────────────────────────

def _validate_result(result: dict) -> dict:
    """
    Takes one item from Claude's response array and validates it.
    
    Two things can go wrong:
    1. Category not in our approved list → default to "Other"
    2. Confidence not a valid 0.0–1.0 float → default to 0.5
    
    We never crash. We always return something usable.
    """
    valid_categories = set(TRANSACTION_CATEGORIES)

    # Validate category
    category = result.get("category", "Other")
    if category not in valid_categories:
        logger.warning(f"Invalid category from Claude: '{category}'. Defaulting to Other.")
        category = "Other"

    # Validate confidence
    confidence = result.get("confidence", 0.5)
    try:
        confidence = float(confidence)
        if confidence < 0.0 or confidence > 1.0:
            confidence = 0.5
    except (TypeError, ValueError):
        confidence = 0.5

    return {
        "id": result.get("id", ""),
        "category": category,
        "confidence": confidence,
        "note": result.get("note", "")
    }


# ── STEP 3 ───────────────────────────────────────────────────────────────
# The actual Claude API call — synchronous (blocking)
# This is intentionally NOT async because the Anthropic SDK is synchronous
# We call this via asyncio.to_thread() so it runs in a background thread
# ─────────────────────────────────────────────────────────────────────────

def _call_claude(batch_with_ids: list[dict]) -> list[dict]:
    """
    Makes the synchronous Claude API call for one batch.
    
    Returns a list of validated result dicts:
    [{"id": "0", "category": "Supplies", "confidence": 0.95, "note": "..."}, ...]
    
    On any failure, returns empty list (caller handles fallback).
    """
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        temperature=0.1,
        system="You are a professional UK bookkeeper. Return only valid JSON arrays.",
        messages=[
            {"role": "user", "content": _build_prompt(batch_with_ids)}
        ]
    )

    response_text = response.content[0].text
    parsed = json.loads(response_text)
    validated = [_validate_result(r) for r in parsed]
    return validated


# ── STEP 4 ───────────────────────────────────────────────────────────────
# Main categorisation function — called by the upload pipeline
# This is async so FastAPI can call it with await
# It splits transactions into batches of 25 and processes each
# ─────────────────────────────────────────────────────────────────────────

async def categorise_transactions(transactions: list[dict]) -> list[dict]:
    """
    Takes a list of transaction dicts and returns them with category,
    confidence, and note fields added.
    
    Input:
        [{"date": "2026-03-07", "description": "TESCO", "amount": -45.50}, ...]
    
    Output (same list, fields added):
        [{"date": "2026-03-07", "description": "TESCO", "amount": -45.50,
          "category": "Supplies", "confidence": 0.95, "note": "Supermarket"}, ...]
    
    Why batches of 25?
    Claude has a context window limit. Sending 500 transactions at once
    could exceed it. Batches of 25 are safe and fast enough.
    
    Why asyncio.to_thread()?
    The Anthropic SDK is synchronous (blocking). If we call it directly
    inside an async function, it freezes the entire FastAPI server while
    waiting for Claude. asyncio.to_thread() runs the blocking call in a
    separate thread — FastAPI stays responsive to other requests.
    """
    if not transactions:
        return []

    results = []

    for i in range(0, len(transactions), BATCH_SIZE):
        batch = transactions[i:i + BATCH_SIZE]

        # Add temporary string IDs so we can map Claude's response
        # back to the correct transaction after the API call
        # id "0" → batch[0], id "1" → batch[1], etc.
        batch_with_ids = [
            {
                "id": str(j),
                "description": t["description"],
                "amount": t["amount"]
            }
            for j, t in enumerate(batch)
        ]

        logger.info(f"Sending batch {i // BATCH_SIZE + 1} — {len(batch_with_ids)} transactions to Claude")

        try:
            # KEY LINE: asyncio.to_thread() runs _call_claude in a background thread
            # await means "pause here until the thread finishes, but let
            # other requests run in the meantime"
            validated = await asyncio.to_thread(_call_claude, batch_with_ids)

            # Build a lookup dict: id → result
            # So we can find each transaction's result by its id instantly
            id_to_result = {r["id"]: r for r in validated}

            # Attach category/confidence/note back to each transaction
            for j, transaction in enumerate(batch):
                result = id_to_result.get(str(j), {})
                transaction["category"] = result.get("category", "Other")
                transaction["confidence"] = result.get("confidence", 0.5)
                transaction["note"] = result.get("note", "")

            results.extend(batch)

        except json.JSONDecodeError as e:
            # Claude returned something that isn't valid JSON
            # This is rare but happens — we fall back gracefully
            logger.error(f"Claude returned invalid JSON for batch {i // BATCH_SIZE + 1}: {e}")
            for transaction in batch:
                transaction["category"] = "Other"
                transaction["confidence"] = 0.5
                transaction["note"] = "Categorisation failed — invalid response"
            results.extend(batch)

        except Exception as e:
            # Network error, API rate limit, etc.
            logger.error(f"Claude API error for batch {i // BATCH_SIZE + 1}: {e}")
            for transaction in batch:
                transaction["category"] = "Other"
                transaction["confidence"] = 0.5
                transaction["note"] = "Categorisation failed — API error"
            results.extend(batch)

    return results