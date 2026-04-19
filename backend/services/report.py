import io
import logging
import asyncio
from datetime import date
from sqlalchemy.orm import Session

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

from backend.database import Transaction
from backend.services.summary import _calculate_summary_data, _call_claude_summary, _build_summary_prompt
from backend.services.forecast import generate_forecast

logger = logging.getLogger(__name__)

# ── Colour palette ─────────────────────────────────────────────────────────
# These match the frontend design exactly
NAVY        = HexColor('#0f1c3f')
BLUE        = HexColor('#2563eb')
LIGHT_BLUE  = HexColor('#eff4ff')
GREEN       = HexColor('#059669')
RED         = HexColor('#dc2626')
AMBER       = HexColor('#d97706')
GREY_LIGHT  = HexColor('#f4f6fb')
GREY_MID    = HexColor('#e8ecf4')
GREY_TEXT   = HexColor('#6b7280')
GREY_DARK   = HexColor('#374151')


# ── STEP 1 ─────────────────────────────────────────────────────────────────
# Build all the styles we'll use throughout the PDF
# ──────────────────────────────────────────────────────────────────────────

def _build_styles():
    """
    Creates and returns a dict of named paragraph styles.

    ReportLab Paragraph styles control: font, size, colour,
    line height, spacing. We define them all in one place so
    we can reuse them consistently across every section.
    """
    base = getSampleStyleSheet()

    styles = {

        # Large white title on the navy header banner
        "title": ParagraphStyle(
            "title",
            fontName="Helvetica-Bold",
            fontSize=22,
            textColor=white,
            spaceAfter=4,
            leading=28,       # line height
        ),

        # Subtitle line under the title (also white)
        "subtitle": ParagraphStyle(
            "subtitle",
            fontName="Helvetica",
            fontSize=10,
            textColor=HexColor('#bfdbfe'),   # pale blue
            spaceAfter=0,
            leading=14,
        ),

        # Section headings like "Financial Summary", "Transactions"
        "section_heading": ParagraphStyle(
            "section_heading",
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=NAVY,
            spaceBefore=16,
            spaceAfter=8,
            leading=16,
        ),

        # Normal body text
        "body": ParagraphStyle(
            "body",
            fontName="Helvetica",
            fontSize=9,
            textColor=GREY_DARK,
            spaceAfter=6,
            leading=14,       # 14pt line height makes text readable
        ),

        # The Claude summary paragraph — slightly larger, more breathing room
        "summary_text": ParagraphStyle(
            "summary_text",
            fontName="Helvetica",
            fontSize=9.5,
            textColor=GREY_DARK,
            spaceAfter=0,
            leading=16,
        ),

        # Small muted label used in the KPI row
        "kpi_label": ParagraphStyle(
            "kpi_label",
            fontName="Helvetica",
            fontSize=7.5,
            textColor=GREY_TEXT,
            spaceAfter=2,
            leading=10,
        ),

        # Large bold number in the KPI row
        "kpi_value": ParagraphStyle(
            "kpi_value",
            fontName="Helvetica-Bold",
            fontSize=16,
            textColor=NAVY,
            spaceAfter=0,
            leading=20,
        ),

        # Small muted footer text at the bottom of the page
        "footer": ParagraphStyle(
            "footer",
            fontName="Helvetica",
            fontSize=7.5,
            textColor=GREY_TEXT,
            alignment=TA_CENTER,
            leading=10,
        ),
    }

    return styles


# ── STEP 2 ─────────────────────────────────────────────────────────────────
# Individual section builders
# Each function returns a list of ReportLab "Flowable" objects.
# Flowables are the building blocks of a PDF — paragraphs, tables,
# spacers, lines. SimpleDocTemplate stacks them top to bottom automatically.
# ──────────────────────────────────────────────────────────────────────────

def _build_header(styles, period_label: str, user_email: str):
    """
    Builds the navy header banner at the top of the PDF.
    Uses a single-cell Table with a navy background — the simplest
    way to get a full-width coloured block in ReportLab.
    """

    # Build the content that goes inside the banner
    # We stack two Paragraphs inside a Table cell
    header_content = [
        Paragraph("FinCopilot", styles["title"]),
        Paragraph(f"Financial Report · {period_label}", styles["subtitle"]),
        Paragraph(f"Generated for: {user_email}", styles["subtitle"]),
    ]

    # A 1×1 table — one row, one column — just for the background colour
    table = Table(
        [[header_content]],     # data = one cell containing our content list
        colWidths=['100%'],
    )

    table.setStyle(TableStyle([
        ('BACKGROUND',  (0, 0), (-1, -1), NAVY),
        ('TOPPADDING',  (0, 0), (-1, -1), 18),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 18),
        ('LEFTPADDING', (0, 0), (-1, -1), 20),
        ('RIGHTPADDING', (0, 0), (-1, -1), 20),
        ('ROUNDEDCORNERS', [6]),
    ]))

    return [table, Spacer(1, 14)]


def _build_kpi_row(styles, summary_data: dict):
    """
    Builds the 4-box KPI row showing Revenue, Expenses, Profit, Anomalies.

    This is a 1-row, 4-column Table.
    Each cell contains a label + value stacked vertically.
    """

    revenue  = summary_data["total_revenue"]
    expenses = summary_data["total_expenses"]
    profit   = summary_data["profit"]
    anomalies = summary_data["anomaly_count"]

    # Helper to format as £1,234.56
    def fmt(n):
        return f"£{n:,.2f}"

    # Build each cell as [label_paragraph, value_paragraph]
    def kpi_cell(label, value_str, value_colour=NAVY):
        value_style = ParagraphStyle(
            f"kpi_val_{label}",
            parent=styles["kpi_value"],
            textColor=value_colour,
        )
        return [
            Paragraph(label.upper(), styles["kpi_label"]),
            Paragraph(value_str, value_style),
        ]

    profit_colour = GREEN if profit >= 0 else RED
    anomaly_colour = AMBER if anomalies > 0 else GREEN

    data = [[
        kpi_cell("Revenue",   fmt(revenue),  GREEN),
        kpi_cell("Expenses",  fmt(expenses), RED),
        kpi_cell("Net Profit", fmt(profit),  profit_colour),
        kpi_cell("Anomalies", str(anomalies), anomaly_colour),
    ]]

    table = Table(data, colWidths=['25%', '25%', '25%', '25%'])

    table.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), GREY_LIGHT),
        ('BOX',           (0, 0), (-1, -1), 0.5, GREY_MID),
        ('INNERGRID',     (0, 0), (-1, -1), 0.5, GREY_MID),
        ('TOPPADDING',    (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING',   (0, 0), (-1, -1), 14),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 14),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('ROUNDEDCORNERS', [4]),
    ]))

    return [table, Spacer(1, 10)]


def _build_summary_section(styles, summary_text: str):
    """
    Builds the plain-English summary section.
    Just a heading + the Claude-generated paragraph.
    """
    elements = []
    elements.append(Paragraph("Financial Summary", styles["section_heading"]))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=GREY_MID, spaceAfter=8))
    elements.append(Paragraph(summary_text, styles["summary_text"]))
    elements.append(Spacer(1, 8))
    return elements


def _build_transactions_section(styles, transactions: list):
    """
    Builds the transaction table.

    ReportLab tables need data as a list of lists (rows × columns).
    First row = header. Remaining rows = one transaction each.
    """
    elements = []
    elements.append(Paragraph("Transactions", styles["section_heading"]))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=GREY_MID, spaceAfter=8))

    if not transactions:
        elements.append(Paragraph("No transactions for this period.", styles["body"]))
        return elements

    # ── Table header row ──
    header_style = ParagraphStyle(
        "th", fontName="Helvetica-Bold", fontSize=7.5,
        textColor=GREY_TEXT, leading=10
    )
    cell_style = ParagraphStyle(
        "td", fontName="Helvetica", fontSize=8,
        textColor=GREY_DARK, leading=11
    )
    amount_style_pos = ParagraphStyle(
        "td_pos", fontName="Helvetica-Bold", fontSize=8,
        textColor=GREEN, leading=11, alignment=TA_RIGHT
    )
    amount_style_neg = ParagraphStyle(
        "td_neg", fontName="Helvetica-Bold", fontSize=8,
        textColor=GREY_DARK, leading=11, alignment=TA_RIGHT
    )
    anomaly_style = ParagraphStyle(
        "td_anom", fontName="Helvetica", fontSize=7.5,
        textColor=AMBER, leading=11
    )

    rows = [[
        Paragraph("DATE", header_style),
        Paragraph("DESCRIPTION", header_style),
        Paragraph("CATEGORY", header_style),
        Paragraph("AMOUNT", ParagraphStyle("th_r", parent=header_style, alignment=TA_RIGHT)),
        Paragraph("FLAG", header_style),
    ]]

    # ── One row per transaction ──
    for t in transactions:
        # Format date as DD Mon (e.g. 15 Mar)
        date_str = t.txn_date.strftime("%d %b") if t.txn_date else ""

        # Truncate long descriptions so they don't overflow the cell
        desc = t.description or ""
        if len(desc) > 38:
            desc = desc[:35] + "..."

        amount = float(t.amount)
        if amount >= 0:
            amount_para = Paragraph(f"+£{amount:,.2f}", amount_style_pos)
        else:
            amount_para = Paragraph(f"£{abs(amount):,.2f}", amount_style_neg)

        # Anomaly flag — show ⚠ with reason tooltip text if flagged
        if t.is_anomaly:
            flag_text = "⚠ Flagged"
            flag_para = Paragraph(flag_text, anomaly_style)
        else:
            flag_para = Paragraph("", cell_style)

        rows.append([
            Paragraph(date_str, cell_style),
            Paragraph(desc, cell_style),
            Paragraph(t.category or "Other", cell_style),
            amount_para,
            flag_para,
        ])

    # Column widths — must add up to page content width
    # A4 = 210mm, margins = 15mm each side → content = 180mm
    col_widths = [18*mm, 65*mm, 42*mm, 30*mm, 25*mm]

    table = Table(rows, colWidths=col_widths, repeatRows=1)
    # repeatRows=1 → header row repeats if table spans multiple pages

    # Style the table
    style_cmds = [
        # Header row background
        ('BACKGROUND',    (0, 0), (-1, 0), GREY_LIGHT),
        ('TOPPADDING',    (0, 0), (-1, 0), 7),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 7),

        # All cells
        ('TOPPADDING',    (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 6),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),

        # Horizontal dividers between rows
        ('LINEBELOW',     (0, 0), (-1, -2), 0.3, GREY_MID),

        # Outer border
        ('BOX',           (0, 0), (-1, -1), 0.5, GREY_MID),
    ]

    # Shade every other data row for readability (zebra striping)
    for i, _ in enumerate(transactions):
        if i % 2 == 0:
            style_cmds.append(
                ('BACKGROUND', (0, i + 1), (-1, i + 1), HexColor('#fafbfd'))
            )

    table.setStyle(TableStyle(style_cmds))

    elements.append(table)
    elements.append(Spacer(1, 10))
    return elements


def _build_anomalies_section(styles, transactions: list):
    """
    Builds the anomalies section — only flagged transactions.
    Shows the reason for each flag.
    """
    elements = []
    anomalies = [t for t in transactions if t.is_anomaly]

    elements.append(Paragraph("Anomalies & Flags", styles["section_heading"]))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=GREY_MID, spaceAfter=8))

    if not anomalies:
        elements.append(Paragraph("✓ No anomalies detected for this period.", styles["body"]))
        return elements

    elements.append(
        Paragraph(
            f"{len(anomalies)} transaction(s) were flagged for review:",
            styles["body"]
        )
    )
    elements.append(Spacer(1, 6))

    reason_style = ParagraphStyle(
        "reason", fontName="Helvetica", fontSize=8,
        textColor=AMBER, leading=11
    )
    cell_style = ParagraphStyle(
        "td", fontName="Helvetica", fontSize=8,
        textColor=GREY_DARK, leading=11
    )

    rows = []
    for t in anomalies:
        date_str = t.txn_date.strftime("%d %b %Y") if t.txn_date else ""
        amount = float(t.amount)
        amount_str = f"+£{amount:,.2f}" if amount >= 0 else f"£{abs(amount):,.2f}"
        reason = t.anomaly_reason or "Flagged by anomaly detection"

        rows.append([
            Paragraph(date_str, cell_style),
            Paragraph((t.description or "")[:40], cell_style),
            Paragraph(amount_str, cell_style),
            Paragraph(reason, reason_style),
        ])

    col_widths = [22*mm, 60*mm, 28*mm, 70*mm]
    table = Table(rows, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 6),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
        ('BACKGROUND',    (0, 0), (-1, -1), HexColor('#fffbeb')),
        ('BOX',           (0, 0), (-1, -1), 0.5, HexColor('#fde68a')),
        ('LINEBELOW',     (0, 0), (-1, -2), 0.3, HexColor('#fde68a')),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 10))
    return elements


def _build_forecast_section(styles, forecast_narrative: str):
    """
    Builds the forecast section with the Claude narrative.
    """
    elements = []
    elements.append(Paragraph("3-Month Cash Flow Forecast", styles["section_heading"]))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=GREY_MID, spaceAfter=8))
    elements.append(Paragraph(forecast_narrative, styles["summary_text"]))
    elements.append(Spacer(1, 8))
    return elements


# ── STEP 3 ─────────────────────────────────────────────────────────────────
# Main PDF builder — assembles all sections into one document
# ──────────────────────────────────────────────────────────────────────────

def _build_pdf(
    summary_data: dict,
    summary_text: str,
    transactions: list,
    forecast_narrative: str,
    period_label: str,
    user_email: str,
) -> bytes:
    """
    Assembles the complete PDF and returns it as bytes.

    Why bytes?
    We never save the PDF to disk. We build it in memory (io.BytesIO),
    then send those bytes directly to the browser. No temp files,
    no cleanup needed.

    io.BytesIO = a file-like object that lives in RAM, not on disk.
    ReportLab writes to it exactly like it would write to a real file.
    """

    buffer = io.BytesIO()

    # SimpleDocTemplate manages page layout automatically
    # It handles margins, page breaks, and flowing content
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15*mm,
        rightMargin=15*mm,
        topMargin=15*mm,
        bottomMargin=15*mm,
        title=f"FinCopilot Report — {period_label}",
        author="FinCopilot",
    )

    styles = _build_styles()

    # Build all sections — each returns a list of Flowables
    # We concatenate them into one big list and hand it to the doc
    elements = []
    elements += _build_header(styles, period_label, user_email)
    elements += _build_kpi_row(styles, summary_data)
    elements += _build_summary_section(styles, summary_text)
    elements += _build_transactions_section(styles, transactions)
    elements += _build_anomalies_section(styles, transactions)
    elements += _build_forecast_section(styles, forecast_narrative)

    # Footer — page number added via a callback function
    def add_footer(canvas, doc):
        """
        Called by ReportLab after every page is drawn.
        canvas = the drawing surface for that page.
        We use it to write the footer text at a fixed position.
        """
        canvas.saveState()
        footer_text = f"FinCopilot · {period_label} · Confidential"
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(GREY_TEXT)
        # drawCentredString(x, y, text) — y=0 is bottom of page
        canvas.drawCentredString(A4[0] / 2, 10*mm, footer_text)
        canvas.restoreState()

    # build() renders all flowables into pages and writes to the buffer
    doc.build(elements, onLaterPages=add_footer, onFirstPage=add_footer)

    # Get the bytes from position 0 of the buffer
    buffer.seek(0)
    return buffer.read()


# ── STEP 4 ─────────────────────────────────────────────────────────────────
# Main async function — called by the API endpoint
# ──────────────────────────────────────────────────────────────────────────

async def generate_report(
    db: Session,
    user_id: str,
    user_email: str,
    start_date: date,
    end_date: date,
    period_label: str,
) -> bytes:
    """
    Orchestrates the full report:
    1. Fetch transactions from DB
    2. Calculate summary data
    3. Call Claude for summary text
    4. Call forecast service for narrative
    5. Build PDF and return bytes

    All Claude calls run in background threads (asyncio.to_thread)
    so they don't block FastAPI's event loop while waiting for the API.
    """
    logger.info(f"Generating report for user {user_id} | {start_date} to {end_date}")

    # ── 1. Fetch transactions ──
    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.txn_date >= start_date,
            Transaction.txn_date < end_date,
        )
        .order_by(Transaction.txn_date.desc())
        .all()
    )

    # ── 2. Calculate summary data ──
    summary_data = _calculate_summary_data(db, user_id, start_date, end_date)

    if not summary_data:
        summary_data = {
            "period_start": start_date.strftime("%d %B %Y"),
            "period_end": end_date.strftime("%d %B %Y"),
            "total_revenue": 0,
            "total_expenses": 0,
            "profit": 0,
            "transaction_count": 0,
            "top_categories": [],
            "anomaly_count": 0,
        }
        summary_text = "No transactions found for this period."
    else:
        # ── 3. Get Claude summary ──
        prompt = _build_summary_prompt(summary_data)
        try:
            summary_text = await asyncio.to_thread(_call_claude_summary, prompt)
        except Exception:
            summary_text = "Summary could not be generated."

    # ── 4. Get forecast narrative ──
    try:
        forecast_result = await generate_forecast(db, user_id)
        forecast_narrative = forecast_result.get("narrative", "Forecast not available.")
    except Exception:
        forecast_narrative = "Forecast could not be generated."

    # ── 5. Build the PDF ──
    # _build_pdf is synchronous (ReportLab is not async)
    # We run it in a thread so it doesn't block FastAPI
    pdf_bytes = await asyncio.to_thread(
        _build_pdf,
        summary_data,
        summary_text,
        transactions,
        forecast_narrative,
        period_label,
        user_email,
    )

    logger.info(f"Report generated — {len(pdf_bytes)} bytes")
    return pdf_bytes