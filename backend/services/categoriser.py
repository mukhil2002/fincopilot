import json
import logging
from anthropic import Anthropic
from backend.config import TRANSACTION_CATEGORIES, ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

client = Anthropic(api_key=ANTHROPIC_API_KEY)

BATCH_SIZE = 25


def _build_prompt(transactions: list[dict]) -> str:
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


def _validate_result(result: dict) -> dict:
    valid_categories = set(TRANSACTION_CATEGORIES)
    
    category = result.get("category", "Other")
    if category not in valid_categories:
        logger.warning(f"Invalid category from Claude: {category}. Defaulting to Other.")
        category = "Other"
    
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


async def categorise_transactions(transactions: list[dict]) -> list[dict]:
    if not transactions:
        return []
    
    results = []
    
    for i in range(0, len(transactions), BATCH_SIZE):
        batch = transactions[i:i + BATCH_SIZE]
        
        batch_with_ids = [
            {"id": str(j), "description": t["description"], "amount": t["amount"]}
            for j, t in enumerate(batch)
        ]
        
        logger.info(f"Categorising batch of {len(batch_with_ids)} transactions")
        
        try:
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
            id_to_result = {r["id"]: r for r in validated}
            
            for j, transaction in enumerate(batch):
                result = id_to_result.get(str(j), {})
                transaction["category"] = result.get("category", "Other")
                transaction["confidence"] = result.get("confidence", 0.5)
                transaction["note"] = result.get("note", "")
            
            results.extend(batch)
            
        except json.JSONDecodeError as e:
            logger.error(f"Claude returned invalid JSON: {e}")
            for transaction in batch:
                transaction["category"] = "Other"
                transaction["confidence"] = 0.5
                transaction["note"] = "Categorisation failed"
            results.extend(batch)
            
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            for transaction in batch:
                transaction["category"] = "Other"
                transaction["confidence"] = 0.5
                transaction["note"] = "Categorisation failed"
            results.extend(batch)
    
    return results