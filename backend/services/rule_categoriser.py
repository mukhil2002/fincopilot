"""
rule_categoriser.py

Rule-based transaction categoriser for RQ2 evaluation.
This is the comparison baseline — it represents the traditional approach
used by commercial tools like Xero and QuickBooks before ML/LLM adoption.

NOT user-facing. Used only by scripts/run_evaluation.py.

Rules are ordered from most specific to least specific.
First match wins — function returns immediately on match.
Default return is "Other" when no rule matches.

Approximately 80 rules across 14 UK SME categories.
Rule sources: HMRC documentation, major UK merchant names,
common bank description patterns from Xero/QuickBooks rule logic.
"""


def categorise_rule_based(description: str, amount: float) -> str:
    """
    Categorises a single UK SME bank transaction using keyword rules.

    Args:
        description: Raw transaction description from bank statement
        amount:      Transaction amount (negative = expense, positive = income)

    Returns:
        One of the 14 standard FinCopilot categories.

    Design notes:
        - Description is uppercased before matching (case-insensitive)
        - Rules checked most-specific first to avoid false matches
        - "HMRC VAT" must be checked before "HMRC" alone
        - Returns "Other" when no rule matches — honest uncertainty
    """

    # Normalise to uppercase for case-insensitive matching
    desc = description.upper().strip()

    # ── GROUP 1: HMRC — Regulatory References ────────────────────────────
    # HMRC uses standardised description formats mandated by UK law.
    # These are the most reliable rules — near-zero false positive rate.
    # Must check specific HMRC types before generic "HMRC" pattern.

    if "HMRC VAT" in desc or "VAT PAYMENT" in desc or "VAT RETURN" in desc:
        return "VAT Payment"

    if "HMRC PAYE" in desc or "PAYE SETTLEMENT" in desc:
        return "Payroll"

    if "HMRC" in desc and "CORPORATION TAX" in desc:
        return "Operating Expenses"

    if "HMRC" in desc and "SELF ASSESSMENT" in desc:
        return "Personal / Drawings"

    # ── GROUP 2: PAYROLL ─────────────────────────────────────────────────
    # Standard UK payroll description patterns.
    # "BACS SALARY" and "WAGES" are common bank payroll descriptors.

    if any(k in desc for k in [
        "PAYROLL", "BACS SALARY", "SALARY PAYMENT",
        "WAGES", "STAFF WAGES", "EMPLOYEE SALARY"
    ]):
        return "Payroll"

    # ── GROUP 3: BANK CHARGES ────────────────────────────────────────────
    # Every major UK bank has a standard monthly charge descriptor.
    # Checking bank name + charge keyword avoids false matches.

    if any(k in desc for k in [
        "BARCLAYS BANK CHARGE", "BARCLAYS MONTHLY FEE",
        "HSBC BANK CHARGE", "HSBC MONTHLY FEE",
        "LLOYDS BANK CHARGE", "LLOYDS MONTHLY FEE",
        "NATWEST BANK CHARGE", "NATWEST MONTHLY FEE",
        "BANK CHARGE", "ACCOUNT FEE", "OVERDRAFT FEE",
        "INTEREST CHARGE", "SERVICE CHARGE FEE"
    ]):
        return "Bank Charges"

    # ── GROUP 4: TRANSFERS ───────────────────────────────────────────────
    # Internal transfers must be separated from income/expenses.
    # A transfer between accounts is not revenue and not an expense.

    if any(k in desc for k in [
        "FASTER PAYMENT", "BACS TRANSFER", "INTERNAL TRANSFER",
        "TRANSFER TO", "TRANSFER FROM", "TFR ", "CHAPS PAYMENT",
        "INTERBANK TRANSFER"
    ]):
        return "Transfers"

    # ── GROUP 5: SOFTWARE & SUBSCRIPTIONS ────────────────────────────────
    # Most extensive group — matches Xero/QuickBooks vendor rule approach.
    # Covers major SaaS tools used by UK SMEs.
    # Listed roughly in order of UK SME usage frequency.

    if any(k in desc for k in [
        # Productivity & Communication
        "MICROSOFT", "MS OFFICE", "OFFICE 365",
        "GOOGLE WORKSPACE", "GSUITE", "G SUITE",
        "SLACK", "ZOOM", "TEAMS",
        "DROPBOX", "ONEDRIVE", "GOOGLE DRIVE",

        # Design & Creative
        "ADOBE", "FIGMA", "CANVA", "SKETCH",

        # Business & CRM
        "SALESFORCE", "HUBSPOT", "PIPEDRIVE",
        "MAILCHIMP", "KLAVIYO", "HOOTSUITE",

        # Accounting software (competitors)
        "XERO", "QUICKBOOKS", "SAGE ", "FREEAGENT",

        # Development & Hosting
        "GITHUB", "GITLAB", "ATLASSIAN", "JIRA",
        "AWS ", "AMAZON WEB SERVICES", "DIGITALOCEAN",
        "HEROKU", "NETLIFY", "VERCEL",

        # Project Management
        "NOTION", "ASANA", "MONDAY.COM", "TRELLO",
        "BASECAMP", "CLICKUP",

        # Other common SaaS
        "SHOPIFY", "SQUARESPACE", "WOOCOMMERCE",
        "SEMRUSH", "AHREFS", "INTERCOM",

        # Consumer subscriptions — common in sole trader accounts
        "SPOTIFY", "NETFLIX", "APPLE.COM/BILL",
        "LINKEDIN PREMIUM", "AMAZON PRIME"
    ]):
        return "Software & Subscriptions"

    # ── GROUP 6: SUPPLIES — UK Retail Merchants ───────────────────────────
    # Major UK supermarkets and office supply retailers.
    # These are the merchants Xero's rule engine has had since day one.
    # Note: AMAZON alone (without WEB SERVICES) defaults here.

    if any(k in desc for k in [
        # Supermarkets
        "TESCO", "SAINSBURY", "ASDA", "MORRISONS",
        "LIDL", "ALDI", "WAITROSE", "CO-OP", "COOP",
        "ICELAND FOODS", "MARKS AND SPENCER", "M&S ",

        # Office & Supplies
        "STAPLES", "RYMAN", "OFFICE DEPOT", "WH SMITH", "WHSMITH",
        "AMAZON",   # catches Amazon marketplace (physical goods)
                    # Note: AMAZON WEB SERVICES already caught in Group 5

        # DIY & Trade
        "SCREWFIX", "TOOLSTATION", "B&Q", "HOMEBASE", "IKEA",
        "HALFORDS",

        # Other common supply merchants
        "COSTCO", "MAKRO", "VIKING DIRECT"
    ]):
        return "Supplies"

    # ── GROUP 7: UTILITIES ────────────────────────────────────────────────
    # Major UK utility providers — energy, water, broadband, mobile.

    if any(k in desc for k in [
        # Energy
        "BRITISH GAS", "EDF ENERGY", "EON ", "E.ON",
        "SCOTTISH POWER", "NPOWER", "OCTOPUS ENERGY",
        "OVO ENERGY", "BULB ENERGY", "SHELL ENERGY",

        # Water
        "THAMES WATER", "SEVERN TRENT", "ANGLIAN WATER",
        "YORKSHIRE WATER", "UNITED UTILITIES", "WELSH WATER",

        # Broadband & Telecoms
        "BT GROUP", "BT BUSINESS", "SKY BROADBAND",
        "VIRGIN MEDIA", "TALK TALK", "TALKTALK",
        "OPENREACH", "PLUSNET",

        # Mobile
        "VODAFONE", "O2 UK", "EE LIMITED", "THREE UK",
        "GIFFGAFF", "LEBARA"
    ]):
        return "Utilities"

    # ── GROUP 8: TRAVEL & TRANSPORT ──────────────────────────────────────
    # UK transport providers and travel merchants.
    # TFL covers all London transport (Tube, bus, Overground).

    if any(k in desc for k in [
        # Ride-hailing
        "UBER", "BOLT ", "FREE NOW", "ADDISON LEE",

        # Public transport
        "TFL ", "TRANSPORT FOR LONDON", "TFL.GOV",
        "NATIONAL RAIL", "TRAINLINE", "THETRAINLINE",
        "AVANTI WEST", "LNER ", "GWR ", "SOUTHERN RAIL",
        "THAMESLINK", "CROSSRAIL", "NATIONAL EXPRESS",

        # Airlines
        "EASYJET", "RYANAIR", "BRITISH AIRWAYS", "WIZZ AIR",
        "JET2", "TUI AIRWAYS",

        # Airports
        "HEATHROW", "GATWICK", "STANSTED", "LUTON AIRPORT",

        # Hotels
        "PREMIER INN", "TRAVELODGE", "HOLIDAY INN",
        "IBIS HOTEL", "MARRIOTT", "HILTON ", "AIRBNB",

        # Car hire
        "ENTERPRISE RENT", "HERTZ ", "AVIS ", "EUROPCAR",
        "SIXT ",

        # Other travel
        "BOOKING.COM", "EXPEDIA", "HOTELS.COM"
    ]):
        return "Travel & Transport"

    # ── GROUP 9: MARKETING & ADVERTISING ─────────────────────────────────
    # Digital marketing platforms used by UK SMEs.

    if any(k in desc for k in [
        "GOOGLE ADS", "GOOGLE ADWORDS",
        "FACEBOOK ADS", "META ADS", "INSTAGRAM ADS",
        "LINKEDIN ADS", "TWITTER ADS", "X ADVERTISING",
        "TIKTOK ADS", "SNAPCHAT ADS",
        "MAILCHIMP",  # also in Software — marketing use case
        "CONSTANT CONTACT", "CAMPAIGN MONITOR",
        "HOOTSUITE ADS", "BUFFER "
    ]):
        return "Marketing & Advertising"

    # ── GROUP 10: PROFESSIONAL FEES ───────────────────────────────────────
    # Freelancers, contractors, legal and accounting professionals.

    if any(k in desc for k in [
        "COMPANIES HOUSE", "COMPANIES HSE",
        "FIVERR", "UPWORK", "FREELANCER.COM", "PEOPLE PER HOUR",
        "SOLICITOR", "LAW FIRM", "LEGAL FEES",
        "ACCOUNTANT FEES", "AUDIT FEES", "CONSULTING FEES",
        "CONTRACTOR PAYMENT", "FREELANCE PAYMENT"
    ]):
        return "Professional Fees"

    # ── GROUP 11: OPERATING EXPENSES ──────────────────────────────────────
    # General business running costs not covered above.

    if any(k in desc for k in [
        # Postage & Courier
        "ROYAL MAIL", "PARCELFORCE", "DHL ", "FEDEX ", "UPS ",
        "EVRI ", "HERMES ", "DPLOCAL", "YODEL ",

        # Office & Premises
        "OFFICE RENT", "BUSINESS RATES", "RATES PAYMENT",
        "CLEANING SERVICES", "WASTE COLLECTION",

        # Insurance
        "INSURANCE", "ZURICH ", "AVIVA ", "AXA ", "HISCOX",
        "SIMPLY BUSINESS", "POLICY BEE",

        # Printing & Stationery
        "VISTAPRINT", "MOOS ", "INSTANTPRINT",

        # Other operational
        "MAINTENANCE", "REPAIR SERVICE", "IT SUPPORT"
    ]):
        return "Operating Expenses"

    # ── GROUP 12: PERSONAL / DRAWINGS ────────────────────────────────────
    # Director drawings, ATM withdrawals, personal expenses.

    if any(k in desc for k in [
        "ATM ", "CASH MACHINE", "CASH WITHDRAWAL",
        "CASHPOINT", "BARCLAYS ATM", "HSBC ATM",
        "DIRECTOR DRAWINGS", "DRAWINGS ",
        "DIVIDEND PAYMENT", "PERSONAL TRANSFER"
    ]):
        return "Personal / Drawings"

    # ── GROUP 13: REVENUE ─────────────────────────────────────────────────
    # If amount is positive and no other rule matched, likely revenue.
    # This is a weak rule — Claude handles this much better.

    if amount > 0 and any(k in desc for k in [
        "PAYMENT FROM", "CLIENT PAYMENT", "INVOICE PAYMENT",
        "BACS RECEIPT", "SALES RECEIPT", "CUSTOMER PAYMENT",
        "RETAINER PAYMENT", "PROJECT PAYMENT"
    ]):
        return "Revenue"

    # ── DEFAULT ───────────────────────────────────────────────────────────
    # No rule matched. Return Other.
    # This is honest — the rule engine doesn't know.
    # This is exactly what real tools do too.

    return "Other"