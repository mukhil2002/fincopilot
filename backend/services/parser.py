import hashlib
import chardet
import pandas as pd
from datetime import datetime
from typing import Optional


# ── STEP 1 ──────────────────────────────────────────────────────────────
# Generate MD5 hash of the file
# This is Deduplication Layer 1 — if the hash matches an existing upload
# for this user, we reject the file immediately before doing any work
# ────────────────────────────────────────────────────────────────────────

def generate_file_hash(file_bytes: bytes) -> str:
    """
    Takes the raw bytes of the uploaded file and returns an MD5 hash string.
    
    MD5 produces a fixed 32-character string from any input.
    Same file = same hash. Always.
    Different file (even one character different) = completely different hash.
    
    Example:
        "TESCO,-45.50" → "a3f2c1d4e5b6..."
    """
    return hashlib.md5(file_bytes).hexdigest()


# ── STEP 2 ──────────────────────────────────────────────────────────────
# Detect file encoding
# UK bank CSVs are not always UTF-8. Barclays and HSBC sometimes export
# Latin-1 encoded files. Reading the wrong encoding = crash or garbled text.
# chardet sniffs the bytes and tells us what encoding to use.
# ────────────────────────────────────────────────────────────────────────

def detect_encoding(file_bytes: bytes) -> str:
    """
    Detects the character encoding of a file from its raw bytes.
    
    Returns the encoding string e.g. 'utf-8', 'ISO-8859-1', 'windows-1252'
    Falls back to 'utf-8' if chardet is not confident.
    """
    result = chardet.detect(file_bytes)
    encoding = result.get("encoding", "utf-8")
    confidence = result.get("confidence", 0)
    
    # If chardet is less than 70% confident, just use utf-8
    # Better to try a safe default than use a wrong encoding
    if confidence < 0.7 or encoding is None:
        return "utf-8"
    
    return encoding


# ── STEP 3 ──────────────────────────────────────────────────────────────
# Auto-detect which columns contain date, description, and amount
# UK banks all use different column names:
#   Monzo:      "Date", "Name", "Amount"
#   Starling:   "Date", "Description", "Amount (GBP)"
#   Barclays:   "Date", "Memo", "Amount"
#   HSBC:       "Date", "Payee", "Paid out", "Paid in"
# We check for all known variants and pick the first match.
# ────────────────────────────────────────────────────────────────────────

# All known column name variants across UK banks
DATE_COLUMNS = ["date", "transaction date", "value date", "posted date", "completed date"]

DESCRIPTION_COLUMNS = [
    "name", "description", "memo", "payee",
    "transaction description", "details", "narrative"
]

AMOUNT_COLUMNS = [
    "amount", "amount (gbp)", "amount (£)", "value",
    "paid out", "paid in", "debit", "credit"
]


def find_column(df_columns: list, candidates: list) -> Optional[str]:
    """
    Given a list of actual column names from the CSV and a list of
    known variants we're looking for, return the first match.
    
    Comparison is case-insensitive — 'Date' matches 'date'.
    
    Returns None if no match found.
    
    Example:
        df_columns = ["Date", "Name", "Amount", "Currency"]
        candidates = ["amount", "amount (gbp)", "value"]
        → returns "Amount"  (case-insensitive match on "amount")
    """
    # Normalise actual columns to lowercase for comparison
    columns_lower = {col.lower(): col for col in df_columns}
    
    for candidate in candidates:
        if candidate.lower() in columns_lower:
            # Return the ORIGINAL column name (with original casing)
            # so pandas can find it
            return columns_lower[candidate.lower()]
    
    return None


# ── STEP 4 ──────────────────────────────────────────────────────────────
# Clean and normalise a single amount value
# Bank CSVs store amounts in all sorts of formats:
#   "£45.50"  →  -45.50  (expense)
#   "45.50"   →  45.50   (could be income or expense depending on context)
#   "(45.50)" →  -45.50  (accounting notation for negative)
#   "1,234.56"→  1234.56 (commas as thousands separator)
# ────────────────────────────────────────────────────────────────────────

def clean_amount(value) -> Optional[float]:
    """
    Takes a raw amount value from a CSV cell and returns a clean float.
    
    Returns None if the value cannot be parsed (row will be skipped).
    """
    if pd.isna(value):
        return None
    
    # Convert to string so we can manipulate it
    value_str = str(value).strip()
    
    if not value_str:
        return None
    
    # Remove currency symbols and spaces
    value_str = value_str.replace("£", "").replace("$", "").replace("€", "")
    value_str = value_str.replace(",", "").replace(" ", "")
    
    # Handle accounting notation: (45.50) means -45.50
    if value_str.startswith("(") and value_str.endswith(")"):
        value_str = "-" + value_str[1:-1]
    
    try:
        return float(value_str)
    except ValueError:
        return None


# ── STEP 5 ──────────────────────────────────────────────────────────────
# Clean and normalise a date value
# UK banks use DD/MM/YYYY. We need YYYY-MM-DD for PostgreSQL.
# We try multiple formats because banks are inconsistent.
# ────────────────────────────────────────────────────────────────────────

DATE_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%d/%m/%Y",    # 07/03/2026  ← most UK banks
    "%d-%m-%Y",    # 07-03-2026
    "%Y-%m-%d",    # 2026-03-07  ← already normalised
    "%d/%m/%y",    # 07/03/26    ← two-digit year
    "%d %b %Y",    # 07 Mar 2026
    "%d %B %Y",    # 07 March 2026
]


def clean_date(value) -> Optional[str]:
    """
    Takes a raw date value from a CSV cell and returns a YYYY-MM-DD string.
    
    Returns None if the date cannot be parsed (row will be skipped).
    """
    if pd.isna(value):
        return None
    
    value_str = str(value).strip()
    
    if not value_str:
        return None
    
    # Try each known format until one works
    for fmt in DATE_FORMATS:
        try:
            parsed = datetime.strptime(value_str, fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    # Nothing worked
    return None


# ── STEP 6 ──────────────────────────────────────────────────────────────
# Main parse function — ties everything together
# This is what the upload endpoint calls.
# Input:  raw bytes of the uploaded file
# Output: file_hash + list of clean transaction dicts
# ────────────────────────────────────────────────────────────────────────

def parse_csv(file_bytes: bytes) -> dict:
    """
    Main entry point for the parser.
    
    Takes raw file bytes, returns:
    {
        "file_hash": "a3f2c1d4...",
        "transactions": [
            {
                "date": "2026-03-07",
                "description": "Tesco Metro",
                "amount": -45.50
            },
            ...
        ],
        "skipped_rows": 2   ← rows we couldn't parse, for logging
    }
    
    Raises ValueError if the file cannot be parsed at all.
    """
    
    # Step 1 — Generate file hash for Layer 1 deduplication
    file_hash = generate_file_hash(file_bytes)
    
    # Step 2 — Detect encoding so we read the file correctly
    encoding = detect_encoding(file_bytes)
    
    # Step 3 — Read CSV into a pandas DataFrame
    # A DataFrame is like a spreadsheet in memory — rows and columns
    # We use io.StringIO to treat the bytes as a file-like object
    # without saving it to disk
    import io
    try:
        decoded = file_bytes.decode(encoding, errors="replace")
        df = pd.read_csv(io.StringIO(decoded))
    except Exception as e:
        raise ValueError(f"Could not read CSV file: {str(e)}")
    
    if df.empty:
        raise ValueError("CSV file is empty")
    
    # Step 4 — Find which columns contain date, description, amount
    date_col = find_column(list(df.columns), DATE_COLUMNS)
    desc_col = find_column(list(df.columns), DESCRIPTION_COLUMNS)
    amount_col = find_column(list(df.columns), AMOUNT_COLUMNS)
    
    # If we can't find the essential columns, we can't parse this file
    if not date_col:
        raise ValueError(
            f"Could not find a date column. Columns found: {list(df.columns)}"
        )
    if not desc_col:
        raise ValueError(
            f"Could not find a description column. Columns found: {list(df.columns)}"
        )
    if not amount_col:
        raise ValueError(
            f"Could not find an amount column. Columns found: {list(df.columns)}"
        )

    
    # Step 5 — Process each row
    transactions = []
    skipped_rows = 0

    # Filter out non-completed transactions (Revolut-specific)
    # Revolut CSVs include PENDING and REVERTED rows.
    # PENDING = not yet settled, amount may change.
    # REVERTED = cancelled transaction, should not be counted.
    # We filter the entire DataFrame before the loop so the loop
    # only ever sees clean, settled transactions.
    if 'State' in df.columns:
        original_count = len(df)
        df = df[df['State'] == 'COMPLETED'] 
        filtered_count = original_count - len(df)
        if filtered_count > 0:
            skipped_rows += filtered_count  # count these as skipped


    
    
    for index, row in df.iterrows():
        # Clean each field
        date = clean_date(row[date_col])
        description = str(row[desc_col]).strip() if not pd.isna(row[desc_col]) else None
        amount = clean_amount(row[amount_col])
        
        # Skip rows where any essential field is missing or unparseable
        if not date or not description or amount is None:
            skipped_rows += 1
            continue
        
        # Skip rows where description is empty after stripping
        if not description:
            skipped_rows += 1
            continue
        
        transactions.append({
            "date": date,
            "description": description,
            "amount": amount
        })
    
    if not transactions:
        raise ValueError("No valid transactions found in this file")
    
    return {
        "file_hash": file_hash,
        "transactions": transactions,
        "skipped_rows": skipped_rows
    }