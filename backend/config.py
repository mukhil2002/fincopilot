import os
from dotenv import load_dotenv

# Load all variables from .env file into the environment
load_dotenv()

# Database
DATABASE_URL = os.getenv("DATABASE_URL")

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Anthropic
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# The 14 transaction categories — single source of truth
TRANSACTION_CATEGORIES = [
    "Revenue",
    "Operating Expenses",
    "Payroll",
    "Supplies",
    "Professional Fees",
    "Software & Subscriptions",
    "Utilities",
    "Travel & Transport",
    "Marketing & Advertising",
    "Bank Charges",
    "VAT Payment",
    "Transfers",
    "Personal / Drawings",
    "Other",
]