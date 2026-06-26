import asyncio
import logging
from datetime import datetime
from collections import defaultdict

import numpy as np
from sqlalchemy.orm import Session
from anthropic import Anthropic

from backend.config import ANTHROPIC_API_KEY
from backend.database import Transaction

logger = logging.getLogger(__name__)

client = Anthropic(api_key=ANTHROPIC_API_KEY)


def _get_monthly_data(db: Session, user_id: str) -> list[dict]:

    transactions = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .all()
    )

    if not transactions:
        return []

    monthly = defaultdict(lambda: {"revenue": 0.0, "expenses": 0.0})

    for t in transactions:
        month_key = t.txn_date.strftime("%Y-%m")
        amount = float(t.amount)

        if amount > 0:
            monthly[month_key]["revenue"] += amount
        elif amount < 0:
            monthly[month_key]["expenses"] += amount

    sorted_months = sorted(monthly.keys())

    result = []
    for month_key in sorted_months:
        result.append({
            "month":    month_key,
            "revenue":  round(monthly[month_key]["revenue"],  2),
            "expenses": round(monthly[month_key]["expenses"], 2),
        })

    return result


def _calculate_forecast(monthly_data: list[dict]) -> dict:

    n = len(monthly_data)

    if n == 0:
        return {"months_of_data": 0}

    revenues = np.array([m["revenue"]  for m in monthly_data])
    expenses = np.array([m["expenses"] for m in monthly_data])

    window       = min(n, 3)
    avg_revenue  = float(np.mean(revenues[-window:]))
    avg_expenses = float(np.mean(expenses[-window:]))

    historical = []
    for m in monthly_data:
        historical.append({
            "month":    m["month"],
            "revenue":  m["revenue"],
            "expenses": m["expenses"],
            "profit":   round(m["revenue"] + m["expenses"], 2),
        })

    last_month_str = monthly_data[-1]["month"]
    last_month_dt  = datetime.strptime(last_month_str, "%Y-%m")

    projected = []
    for i in range(1, 4):
        month_num = last_month_dt.month + i
        year      = last_month_dt.year

        if month_num > 12:
            month_num -= 12
            year += 1

        projected_month_str = f"{year}-{month_num:02d}"

        projected.append({
            "month":    projected_month_str,
            "revenue":  round(avg_revenue,  2),
            "expenses": round(avg_expenses, 2),
            "profit":   round(avg_revenue + avg_expenses, 2),
        })

    return {
        "months_of_data":       n,
        "historical":           historical,
        "projected":            projected,
        "avg_monthly_revenue":  round(avg_revenue,  2),
        "avg_monthly_expenses": round(avg_expenses, 2),
        "avg_monthly_profit":   round(avg_revenue + avg_expenses, 2),
    }


def _build_forecast_prompt(forecast_data: dict) -> str:

    n          = forecast_data["months_of_data"]
    projected  = forecast_data["projected"]

    projections_text = "\n".join(
        f"  - {p['month']}: Revenue £{p['revenue']:,.2f} | "
        f"Expenses £{abs(p['expenses']):,.2f} | "
        f"Profit £{p['profit']:,.2f}"
        for p in projected
    )

    if n == 1:
        confidence_note = (
            "IMPORTANT: This forecast is based on only 1 month of data. "
            "Make clear this is very early and the owner should upload more "
            "months for a reliable forecast."
        )
    elif n == 2:
        confidence_note = (
            "IMPORTANT: This forecast is based on only 2 months of data. "
            "Mention the forecast will improve with more months of history."
        )
    else:
        confidence_note = (
            "This forecast is based on a solid rolling average. "
            "Give one specific, actionable recommendation."
        )

    prompt = f"""Here is the 3-month cash flow forecast for a UK small business owner.

Based on {n} month(s) of historical data.

Average monthly figures used for projection:
  - Revenue:  £{forecast_data['avg_monthly_revenue']:,.2f}
  - Expenses: £{abs(forecast_data['avg_monthly_expenses']):,.2f}
  - Profit:   £{forecast_data['avg_monthly_profit']:,.2f}

Projected next 3 months:
{projections_text}

{confidence_note}

Write a short 3-4 sentence narrative for this forecast.
- Plain English, no accounting jargon
- Use £ for currency
- Be specific with the numbers
- End with one concrete recommendation the owner can act on"""

    return prompt


def _call_claude_forecast(prompt: str) -> str:

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        temperature=0.3,
        system=(
            "You are a financial advisor giving a cash flow forecast to a "
            "UK small business owner. Be factual, clear, and encouraging. "
            "Use plain English. Always use £ for currency."
        ),
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return response.content[0].text


async def generate_forecast(db: Session, user_id: str) -> dict:

    logger.info(f"Generating forecast for user {user_id}")

    monthly_data = _get_monthly_data(db, user_id)

    if not monthly_data:
        logger.warning(f"No transaction data found for user {user_id}")
        return {
            "months_of_data":       0,
            "historical":           [],
            "projected":            [],
            "narrative":            (
                "No transaction data found. Upload a bank statement "
                "to generate your cash flow forecast."
            ),
            "avg_monthly_revenue":  0.0,
            "avg_monthly_expenses": 0.0,
            "avg_monthly_profit":   0.0,
        }

    forecast_data = _calculate_forecast(monthly_data)

    prompt = _build_forecast_prompt(forecast_data)

    logger.info(
        f"Calling Claude for forecast — "
        f"{forecast_data['months_of_data']} months of data"
    )
    narrative = await asyncio.to_thread(_call_claude_forecast, prompt)

    logger.info("Forecast generated successfully")

    return {
        "months_of_data":       forecast_data["months_of_data"],
        "historical":           forecast_data["historical"],
        "projected":            forecast_data["projected"],
        "narrative":            narrative,
        "avg_monthly_revenue":  forecast_data["avg_monthly_revenue"],
        "avg_monthly_expenses": forecast_data["avg_monthly_expenses"],
        "avg_monthly_profit":   forecast_data["avg_monthly_profit"],
    }