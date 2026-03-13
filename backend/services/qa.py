import asyncio
import logging
from datetime import date
from sqlalchemy.orm import Session
from anthropic import Anthropic
from backend.config import ANTHROPIC_API_KEY
from backend.database import Transaction

logger = logging.getLogger(__name__)

client = Anthropic(api_key=ANTHROPIC_API_KEY)


# ── STEP 1 ────────────────────────────────────────────────────────────────
# Fetch transactions from DB and format them for Claude
# ─────────────────────────────────────────────────────────────────────────

def _fetch_transactions(
    db: Session,
    user_id: str,
    start_date: date | None,
    end_date: date | None
) -> list[dict]:
    """
    Fetches transactions and converts them to simple dicts.

    Why convert to dicts instead of sending SQLAlchemy objects?
    SQLAlchemy model objects can't be serialised to text directly.
    We only send Claude what it needs — date, description,
    amount, category. Nothing else.

    start_date and end_date are optional — if not provided,
    we return ALL transactions for this user.
    """
    query = db.query(Transaction).filter(
        Transaction.user_id == user_id
    )

    # Only apply date filters if provided
    if start_date:
        query = query.filter(Transaction.txn_date >= start_date)
    if end_date:
        query = query.filter(Transaction.txn_date <= end_date)

    # Order by date so Claude sees them chronologically
    transactions = query.order_by(Transaction.txn_date.asc()).all()

    # Convert to plain dicts — only the fields Claude needs
    return [
        {
            "date": t.txn_date.strftime("%d %b %Y"),
            "description": t.description,
            "amount": float(t.amount),
            "category": t.category or "Other"
        }
        for t in transactions
    ]


# ── STEP 2 ────────────────────────────────────────────────────────────────
# Build the prompt — transactions + question
# ─────────────────────────────────────────────────────────────────────────

def _build_qa_prompt(transactions: list[dict], question: str) -> str:
    """
    Formats the transaction list and question into a prompt.

    We format transactions as readable lines rather than JSON.
    Easier for Claude to read quickly when scanning for answers.

    Example line:
    07 Mar 2026 | TESCO STORES | -£45.50 | Supplies
    """

    # Format each transaction as a readable line
    lines = []
    for t in transactions:
        amount = t["amount"]
        # Show £ sign with +/- to make income vs expense clear
        amount_str = f"+£{amount:.2f}" if amount > 0 else f"-£{abs(amount):.2f}"
        lines.append(
            f"{t['date']} | {t['description']} | {amount_str} | {t['category']}"
        )

    transactions_text = "\n".join(lines)

    prompt = f"""Here are the financial transactions for this UK small business:

{transactions_text}

Question: {question}

Answer the question using only the transaction data above.
- Be specific with amounts and dates
- Use £ for currency
- If the answer cannot be found in the data, say so clearly
- Keep the answer concise and direct"""

    return prompt


# ── STEP 3 ────────────────────────────────────────────────────────────────
# The synchronous Claude call
# ─────────────────────────────────────────────────────────────────────────

def _call_claude_qa(prompt: str) -> str:
    """
    Calls Claude and returns the answer as a string.
    Same pattern as summary — synchronous, run via asyncio.to_thread().
    """
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        temperature=0.4,
        system=(
            "You are a financial assistant for a UK small business owner. "
            "Answer questions about their transactions accurately and concisely. "
            "Only use the transaction data provided. Never invent figures. "
            "If you cannot answer from the data, say so clearly."
        ),
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return response.content[0].text


# ── STEP 4 ────────────────────────────────────────────────────────────────
# Main function — called by the API endpoint
# ─────────────────────────────────────────────────────────────────────────

async def answer_question(
    db: Session,
    user_id: str,
    question: str,
    start_date: date | None = None,
    end_date: date | None = None
) -> dict:
    """
    Orchestrates the full Q&A flow.

    start_date and end_date are optional.
    If not provided — Claude searches ALL transactions.
    If provided — Claude only sees that date range.

    Returns:
        {
            "answer": "Your biggest expense category is Payroll at £4,200...",
            "transaction_count": 47
        }
    """
    logger.info(f"Q&A request for user {user_id} | question: {question[:50]}...")

    # Fetch transactions
    transactions = _fetch_transactions(db, user_id, start_date, end_date)

    if not transactions:
        logger.warning(f"No transactions found for user {user_id}")
        return {
            "answer": "No transactions found for the selected period. Upload a bank statement to get started.",
            "transaction_count": 0
        }

    logger.info(f"Sending {len(transactions)} transactions to Claude for Q&A")

    # Build prompt and call Claude
    prompt = _build_qa_prompt(transactions, question)
    answer = await asyncio.to_thread(_call_claude_qa, prompt)

    logger.info("Q&A answer generated successfully")

    return {
        "answer": answer,
        "transaction_count": len(transactions)
    }