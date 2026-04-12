// TransactionRow.jsx
// Renders one transaction as a table row
// Uses CategoryBadge + ConfidenceBar built in Steps 1 and 2
// Has three visual states:
//   Normal row     → plain white background
//   Anomaly row    → faint amber tint + amber dot on description
//   Low confidence → faint red tint on the row

import { CategoryBadge } from '../ui/CategoryBadge'
import { ConfidenceBar } from '../ui/ConfidenceBar'

// ── Date formatter ────────────────────────────────────────────────
// Converts "2026-03-14" (ISO string from backend) → "14 Mar"
// We don't need the year — user already selected the month
// Intl.DateTimeFormat is the browser's built-in date formatter
// 'en-GB' = British English format (day before month)
function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',   // "Mar" not "March"
  })
}

// ── Amount formatter ──────────────────────────────────────────────
// Converts -45.50 → "−£45.50"  |  5000 → "+£5,000"
// Uses the browser's Intl.NumberFormat for correct £ symbol + commas
function formatAmount(amount) {
  const num = Number(amount)
  // Intl.NumberFormat formats the number with £ symbol and commas
  const formatted = new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'GBP',
  }).format(Math.abs(num))   // Math.abs = always positive for formatting
                              // we add the +/- sign manually below

  // Positive = income → prefix with +
  // Negative = expense → prefix with − (minus sign, already in formatted)
  return num > 0 ? `+${formatted}` : `-${formatted}`
}

// ── Component ─────────────────────────────────────────────────────
// Props:
//   txn       = one transaction object from your API
//               { id, txn_date, description, amount, category,
//                 confidence, is_anomaly, anomaly_reason, ... }
//   onCorrect = function called when user clicks the category badge
//               or the edit pencil — triggers correction dropdown
export function TransactionRow({ txn, onCorrect }) {

  // Derive two boolean flags for visual state
  // Number() because confidence can come back as a string from the API
  const isAnomaly = txn.is_anomaly
  const isLowConf = Number(txn.confidence) < 0.70

  // ── Row background colour logic ───────────────────────────────
  // Anomaly rows get a faint amber tint — draws the eye gently
  // Low confidence rows get a faint red tint — signals review needed
  // Normal rows have no background — clean white
  // Anomaly takes priority over low confidence if both are true
  let rowBackground
  if (isAnomaly) {
    rowBackground = 'rgba(255,251,235,0.33)'  // very faint amber
  } else if (isLowConf) {
    rowBackground = 'rgba(254,242,242,0.27)'  // very faint red
  } else {
    rowBackground = undefined                  // default white
  }

  return (
    // "group" class is a Tailwind trick — it lets child elements
    // react to the parent row being hovered
    // e.g. the edit pencil uses "group-hover:opacity-100"
    // meaning: "show me when the parent row is hovered"
    <tr
      className="group transition-colors hover:bg-[#fafbff]"
      style={{
        background: rowBackground,
        borderBottom: '1px solid #f7f8fc',
      }}
    >

      {/* ── Column 1: Date ─────────────────────────────────────── */}
      <td
        className="px-3.5 py-2.5 text-[11px] whitespace-nowrap"
        style={{ color: '#9ca3af' }}   // muted grey — supporting info
      >
        {formatDate(txn.txn_date)}
      </td>

      {/* ── Column 2: Description ──────────────────────────────── */}
      <td className="px-3.5 py-2.5">
        <div className="flex items-center gap-1.5">

          {/* Amber dot — only shown if this transaction is an anomaly */}
          {/* title= shows the reason as a tooltip on hover */}
          {/* This tiny dot is the user's first alert that something */}
          {/* needs attention — they hover to see why */}
          {isAnomaly && (
            <span
              title={txn.anomaly_reason || 'Anomaly detected'}
              className="w-1.5 h-1.5 rounded-full flex-shrink-0 cursor-help"
              style={{ background: '#f59e0b' }}   // amber dot
            />
          )}

          {/* Transaction description — truncated if too long */}
          {/* maxWidth prevents long merchant names breaking the layout */}
          <span
            className="text-[12px] font-medium truncate"
            style={{ color: '#1f2937', maxWidth: 200 }}
          >
            {txn.description}
          </span>
        </div>
      </td>

      {/* ── Column 3: Category Badge ────────────────────────────── */}
      <td className="px-3.5 py-2.5">
        {/* Pass onCorrect so clicking the badge triggers correction */}
        {/* CategoryBadge handles the cursor + tooltip automatically */}
        <CategoryBadge
          category={txn.category}
          onClick={(e) => onCorrect(txn, e)}
        />
      </td>

      {/* ── Column 4: Amount ────────────────────────────────────── */}
      <td
        className="px-3.5 py-2.5 text-right text-[12px] font-semibold tabular-nums"
        style={{
          // Positive amount = green (income/revenue)
          // Negative amount = dark grey (expense)
          color: Number(txn.amount) > 0 ? '#059669' : '#374151',
        }}
      >
        {formatAmount(txn.amount)}
      </td>

      {/* ── Column 5: Confidence Bar ─────────────────────────────── */}
      <td className="px-3.5 py-2.5">
        <ConfidenceBar confidence={Number(txn.confidence)} />
      </td>

      {/* ── Column 6: Edit Pencil ────────────────────────────────── */}
      {/* Hidden by default — appears only when the row is hovered */}
      {/* "opacity-0 group-hover:opacity-100" = invisible until hover */}
      {/* This keeps rows clean — only shows the edit option when needed */}
      <td className="px-2 py-2.5">
        <button
          onClick={(e) => onCorrect(txn, e)}
          className="opacity-0 group-hover:opacity-100 transition-opacity text-[13px]"
          style={{ color: '#d1d5db' }}
          onMouseEnter={e => { e.currentTarget.style.color = '#2563eb' }}
          onMouseLeave={e => { e.currentTarget.style.color = '#d1d5db' }}
          title="Correct category"
        >
          ✎
        </button>
      </td>

    </tr>
  )
}   