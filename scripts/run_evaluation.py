"""
run_evaluation.py

Evaluates two transaction categorisation approaches:
rule-based keyword matching vs Claude zero-shot LLM.

Reads datasets from scripts/datasets/, runs both categorisers,
measures accuracy against ground truth, and saves timestamped
results to the results/ folder.

Usage:
    python scripts/run_evaluation.py
"""

import os
import sys
import csv
import json
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic

# ── Setup ─────────────────────────────────────────────────────────────────
# Add project root to Python path so we can import from backend/
# This is needed because we import TRANSACTION_CATEGORIES from config.py
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env so ANTHROPIC_API_KEY is available
load_dotenv(PROJECT_ROOT / ".env")

# Now we can import from backend
from backend.config import TRANSACTION_CATEGORIES, ANTHROPIC_API_KEY
from backend.services.rule_categoriser import categorise_rule_based

# Anthropic client — same model as the app
client = Anthropic(api_key=ANTHROPIC_API_KEY)
MODEL = "claude-sonnet-4-6"
TEMPERATURE = 0.1   # same as the app — consistent and fair


# ── Claude single-transaction call ────────────────────────────────────────

def categorise_with_claude(description: str, amount: float) -> tuple:
    """
    Calls Claude to categorise a single transaction.
    Returns (category, confidence) tuple.

    Why single transaction here (not batch of 25)?
    The app uses batches for efficiency — one API call for 25 transactions.
    Here we need per-transaction results for accuracy measurement.
    Batching would require extra unpacking logic with no benefit for a
    300-transaction research script.

    Same model, same temperature, same category list as the app.
    Only the format is different — one transaction instead of a batch.
    """
    categories_str = "\n".join(f"- {c}" for c in TRANSACTION_CATEGORIES)

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=150,
            temperature=TEMPERATURE,
            system="You are a professional UK bookkeeper. Return only valid JSON. No explanation.",
            messages=[{
                "role": "user",
                "content": (
                    f"Categorise this UK SME bank transaction into exactly one category.\n\n"
                    f"Categories:\n{categories_str}\n\n"
                    f"Transaction:\n"
                    f"Description: {description}\n"
                    f"Amount: £{amount}\n\n"
                    f"Return format: {{\"category\": \"Category Name\", \"confidence\": 0.95}}"
                )
            }]
        )

        result = json.loads(response.content[0].text)
        category = result.get("category", "Other")
        confidence = float(result.get("confidence", 0.5))

        # Validate — same logic as categoriser.py
        if category not in TRANSACTION_CATEGORIES:
            category = "Other"
        if confidence < 0.0 or confidence > 1.0:
            confidence = 0.5

        return category, confidence

    except Exception as e:
        # Any failure — network, JSON parse, rate limit — defaults to Other
        print(f"    [Claude error] {description[:40]} → {e}")
        return "Other", 0.5


# ── Dataset loader ────────────────────────────────────────────────────────

def load_dataset(filepath: str) -> list:
    """
    Loads a synthetic dataset CSV.

    Expected columns:
        id, description, amount, true_category

    Returns list of dicts, one per transaction.
    Skips the header row automatically (csv.DictReader handles this).
    """
    transactions = []

    with open(filepath, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            transactions.append({
                "id":            row["id"],
                "description":   row["description"],
                "amount":        float(row["amount"]),
                "true_category": row["true_category"],
            })

    return transactions


# ── Single dataset evaluation ─────────────────────────────────────────────

def evaluate_dataset(dataset_name: str, transactions: list) -> dict:
    """
    Runs both categorisers on every transaction in a dataset.
    Measures accuracy for each.
    Returns results dict with per-transaction details and summary metrics.

    Accuracy = correct predictions / total transactions
    A prediction is correct when it exactly matches true_category.
    """

    total = len(transactions)
    rule_correct = 0
    claude_correct = 0
    rows = []

    print(f"\n{'─' * 55}")
    print(f"  {dataset_name} ({total} transactions)")
    print(f"{'─' * 55}")

    for i, txn in enumerate(transactions):

        # ── Rule-based ──────────────────────────────────────────
        # Instant — no API call, no delay
        rule_prediction = categorise_rule_based(
            txn["description"], txn["amount"]
        )
        rule_match = rule_prediction == txn["true_category"]
        if rule_match:
            rule_correct += 1

        # ── Claude ──────────────────────────────────────────────
        # API call — takes ~1 second per transaction
        claude_prediction, claude_confidence = categorise_with_claude(
            txn["description"], txn["amount"]
        )
        claude_match = claude_prediction == txn["true_category"]
        if claude_match:
            claude_correct += 1

        # ── Record result ───────────────────────────────────────
        rows.append({
            "dataset":            dataset_name,
            "id":                 txn["id"],
            "description":        txn["description"],
            "amount":             txn["amount"],
            "true_category":      txn["true_category"],
            "rule_prediction":    rule_prediction,
            "rule_correct":       rule_match,
            "claude_prediction":  claude_prediction,
            "claude_confidence":  round(claude_confidence, 2),
            "claude_correct":     claude_match,
        })

        # ── Progress ────────────────────────────────────────────
        # Print every 10 transactions so you know it's working
        if (i + 1) % 10 == 0 or (i + 1) == total:
            print(f"  [{i + 1:3d}/{total}] "
                  f"Rule: {rule_correct}/{i+1} correct  |  "
                  f"Claude: {claude_correct}/{i+1} correct")

        # Small delay between Claude calls to avoid rate limiting
        # 0.3 seconds × 100 transactions = 30 seconds per dataset
        time.sleep(0.3)

    rule_accuracy    = rule_correct / total
    claude_accuracy  = claude_correct / total

    print(f"\n  Rule-based:  {rule_accuracy:.1%}  ({rule_correct}/{total})")
    print(f"  Claude:      {claude_accuracy:.1%}  ({claude_correct}/{total})")
    print(f"  Difference:  +{claude_accuracy - rule_accuracy:.1%} in favour of Claude")

    return {
        "dataset_name":    dataset_name,
        "total":           total,
        "rule_correct":    rule_correct,
        "rule_accuracy":   rule_accuracy,
        "claude_correct":  claude_correct,
        "claude_accuracy": claude_accuracy,
        "rows":            rows,
    }


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    """
    Runs the full evaluation across all three datasets.
    Saves two output files with a timestamp in the filename
    so every run is preserved and files never overwrite each other.
    """

    # ── Dataset paths ────────────────────────────────────────────
    datasets_dir = PROJECT_ROOT / "scripts" / "datasets"

    datasets = [
        ("Dataset 1 — Clean Business",   datasets_dir / "clean_business.csv"),
        ("Dataset 2 — Ambiguous",         datasets_dir / "ambiguous.csv"),
        ("Dataset 3 — Mixed Sole Trader", datasets_dir / "mixed_sole_trader.csv"),
    ]

    # ── Output setup ─────────────────────────────────────────────
    # Timestamp format: 2026-07-06_14-23-11
    # Added to every output filename so runs never overwrite each other
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    results_dir = PROJECT_ROOT / "results"
    results_dir.mkdir(exist_ok=True)   # create results/ if it doesn't exist

    summary_path     = results_dir / f"evaluation_{timestamp}_summary.csv"
    full_results_path = results_dir / f"evaluation_{timestamp}_full.csv"

    print(f"\n{'=' * 55}")
    print(f"  FinCopilot RQ2 Evaluation")
    print(f"  {timestamp}")
    print(f"{'=' * 55}")
    print(f"  Model:       {MODEL}")
    print(f"  Temperature: {TEMPERATURE}")
    print(f"  Categories:  {len(TRANSACTION_CATEGORIES)}")

    # ── Run evaluation ────────────────────────────────────────────
    all_rows    = []
    summaries   = []

    for dataset_name, filepath in datasets:
        if not filepath.exists():
            print(f"\n  WARNING: {filepath.name} not found — skipping")
            continue

        metrics = evaluate_dataset(dataset_name, load_dataset(str(filepath)))

        all_rows.extend(metrics["rows"])
        summaries.append({
            "dataset":          metrics["dataset_name"],
            "total":            metrics["total"],
            "rule_correct":     metrics["rule_correct"],
            "rule_accuracy":    f"{metrics['rule_accuracy']:.1%}",
            "claude_correct":   metrics["claude_correct"],
            "claude_accuracy":  f"{metrics['claude_accuracy']:.1%}",
            "difference":       f"+{metrics['claude_accuracy'] - metrics['rule_accuracy']:.1%}",
        })

    # ── Save full results CSV ─────────────────────────────────────
    if all_rows:
        with open(full_results_path, "w", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=all_rows[0].keys())
            writer.writeheader()
            writer.writerows(all_rows)
        print(f"\n  Full results saved → {full_results_path.name}")

    # ── Save summary CSV ──────────────────────────────────────────
    if summaries:
        with open(summary_path, "w", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=summaries[0].keys())
            writer.writeheader()
            writer.writerows(summaries)
        print(f"  Summary saved      → {summary_path.name}")

    # ── Print final table ─────────────────────────────────────────
    print(f"\n{'=' * 55}")
    print(f"  FINAL RESULTS")
    print(f"{'=' * 55}")
    print(f"  {'Dataset':<32} {'Rule':>6}  {'Claude':>6}  {'Δ':>6}")
    print(f"  {'─' * 51}")
    for s in summaries:
        name = s["dataset"].replace("Dataset ", "DS")
        print(f"  {name:<32} {s['rule_accuracy']:>6}  {s['claude_accuracy']:>6}  {s['difference']:>6}")

    # ── Benchmark comparison ──────────────────────────────────────
    print(f"\n{'=' * 55}")
    print(f"  BENCHMARK COMPARISON — Aluffi et al. (2025)")
    print(f"{'=' * 55}")
    print(f"  GPT-4o zero-shot:          60.4%")
    print(f"  GPT-4o fine-tuned:         73.49%")
    print(f"  Claude this study (DS2):   see Dataset 2 result above")
    print(f"{'=' * 55}\n")


if __name__ == "__main__":
    main()