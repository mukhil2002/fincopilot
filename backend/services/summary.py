import asyncio
import logging
from datetime import date
from sqlalchemy.orm import Session
from anthropic import APIStatusError, Anthropic
from backend.config import ANTHROPIC_API_KEY
from backend.database import Transaction

logger = logging.getLogger(__name__)

# One client, reused for every call — same pattern as categoriser.py
client = Anthropic(api_key=ANTHROPIC_API_KEY)


# ── STEP 1 ────────────────────────────────────────────────────────────────
# Fetch and calculate — pure Python, no Claude yet
# ─────────────────────────────────────────────────────────────────────────

def _calculate_summary_data(
    db: Session,
    user_id: str,
    start_date: date,
    end_date: date
) -> dict:
    """
    Queries the database and calculates financial totals.
    Returns a dict of numbers — no Claude involvement here.

    Why separate from Claude call?
    Single responsibility principle — one function does the maths,
    another function talks to Claude. Easier to debug and test.
    """

    # Fetch all transactions for this user in the date range
    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.txn_date >= start_date,
            Transaction.txn_date <= end_date
        )
        .all()
    )

    if not transactions:
        return None

    # Separate income (positive amounts) from expenses (negative amounts)
    # In UK bank statements: money in = positive, money out = negative
    revenue_txns = [t for t in transactions if float(t.amount) > 0]
    expense_txns = [t for t in transactions if float(t.amount) < 0]

    total_revenue = sum(float(t.amount) for t in revenue_txns)
    total_expenses = abs(sum(float(t.amount) for t in expense_txns))
    profit = total_revenue - total_expenses

    # Calculate spending per category
    # We only look at expense transactions for category breakdown
    category_totals = {}
    for t in expense_txns:
        cat = t.category or "Other"
        category_totals[cat] = category_totals.get(cat, 0) + abs(float(t.amount))

    # Sort categories by amount spent, largest first
    sorted_categories = sorted(
        category_totals.items(),
        key=lambda x: x[1],
        reverse=True
    )

    # Count anomalies in this period
    anomaly_count = sum(1 for t in transactions if t.is_anomaly)

    return {
        "period_start": start_date.strftime("%d %B %Y"),
        "period_end": end_date.strftime("%d %B %Y"),
        "total_revenue": round(total_revenue, 2),
        "total_expenses": round(total_expenses, 2),
        "profit": round(profit, 2),
        "transaction_count": len(transactions),
        "top_categories": sorted_categories[:5],  # top 5 only
        "anomaly_count": anomaly_count,
    }


# ── STEP 2 ────────────────────────────────────────────────────────────────
# Build the prompt — inject the calculated numbers
# ─────────────────────────────────────────────────────────────────────────

def _build_summary_prompt(data: dict) -> str:
    """
    Builds the message we send to Claude.
    We give Claude the numbers — it writes the words.
    """

    # Format top categories as readable lines
    categories_text = "\n".join(
        f"  - {cat}: £{amount:.2f}"
        for cat, amount in data["top_categories"]
    )

    prompt = f"""Here is the financial data for a UK small business owner for the period {data['period_start']} to {data['period_end']}:

Total Revenue: £{data['total_revenue']:.2f}
Total Expenses: £{data['total_expenses']:.2f}
Net Profit: £{data['profit']:.2f}
Total Transactions: {data['transaction_count']}
Anomalies Flagged: {data['anomaly_count']}

Top Expense Categories:
{categories_text}

Write a clear, friendly financial summary for this business owner. They have no accounting background.
- Use plain English, no jargon
- Mention the profit margin as a percentage
- Highlight the biggest expense category
- If anomalies were flagged, mention they should review them
- Keep it to 3-4 sentences
- Use £ for currency, not $"""

    return prompt


# ── STEP 3 ────────────────────────────────────────────────────────────────
# The synchronous Claude call — same pattern as categoriser.py
# ─────────────────────────────────────────────────────────────────────────

def _call_claude_summary(prompt: str) -> str:
    try:
        
        """
        Calls Claude synchronously and returns the summary text.
        Run via asyncio.to_thread() so it doesn't block FastAPI.
        """
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            temperature=0.4,  # warmer tone for readable English, not robotic
            system=(
                "You are a friendly financial advisor speaking to a small business "
                "owner with no accounting background. Write clear, encouraging, "
                "plain-English summaries. Be specific with numbers."
            ),
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.content[0].text
    except APIStatusError as e:
        if e.status_code == 529:
            raise RuntimeError("Claude API is temporarily overloaded. Please try again in a moment.")
        raise


# ── STEP 4 ────────────────────────────────────────────────────────────────
# Main function — called by the API endpoint
# ─────────────────────────────────────────────────────────────────────────

async def generate_summary(
    db: Session,
    user_id: str,
    start_date: date,
    end_date: date
) -> dict:
    """
    Orchestrates the full summary flow.
    Called by the API endpoint with await.

    Returns:
        {
            "summary": "March was a solid month...",
            "data": { revenue, expenses, profit, ... }
        }
    """
    logger.info(f"Generating summary for user {user_id} | {start_date} to {end_date}")

    # Step 1: Calculate the numbers from DB
    summary_data = _calculate_summary_data(db, user_id, start_date, end_date)

    if not summary_data:
        logger.warning(f"No transactions found for user {user_id} in date range")
        return {
            "summary": "No transactions found for the selected period. Upload a bank statement to get started.",
            "data": None
        }

    # Step 2: Build the prompt
    prompt = _build_summary_prompt(summary_data)

    # Step 3: Call Claude in a background thread
    logger.info(f"Calling Claude for summary — {summary_data['transaction_count']} transactions")
    
    try:
        summary_text = await asyncio.to_thread(_call_claude_summary, prompt)
        logger.info("Summary generated successfully")
        return {
            "summary": summary_text,
            "data": summary_data
        }

    except RuntimeError as e:
        return {
            "summary": str(e),  # ← the overload message
            "data": summary_data
        }