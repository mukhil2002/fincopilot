import { useState, useEffect } from 'react'
import api from '../../lib/api'

// ── Helper: turn "2026-03" into { start_date, end_date } ──────────────
// We need the first and last day of the selected month.
//
// Why do we need this?
// The backend expects full dates: "2026-03-01" and "2026-03-31"
// Dashboard only stores "2026-03" (year-month) so we derive the rest here.
//
// new Date(year, month, 0) is a JavaScript trick:
// Day 0 of a month = the LAST day of the PREVIOUS month.
// So new Date(2026, 3, 0) = last day of March 2026 = 31st March.
// (months are 0-indexed in JS, so month 3 = April, day 0 = 31 March)

function getMonthRange(yearMonth) {
  const [year, month] = yearMonth.split('-').map(Number)
  const firstDay = `${yearMonth}-01`
  const lastDay = new Date(year, month, 0).getDate() // e.g. 31
  const endDate = `${yearMonth}-${String(lastDay).padStart(2, '0')}`
  return { start_date: firstDay, end_date: endDate }
}

// ── Loading skeleton ───────────────────────────────────────────────────
// Shown while we wait for Claude to respond.
// Three lines of different widths → looks like text is about to appear.
// animate-pulse is a Tailwind class that fades in/out repeatedly.

function SummarySkeleton() {
  return (
    <div className="space-y-2">
      {[100, 85, 70].map((width) => (
        <div
          key={width}
          className="h-3 rounded-full animate-pulse"
          style={{ background: '#f0f3f9', width: `${width}%` }}
        />
      ))}
    </div>
  )
}

// ── Main component ─────────────────────────────────────────────────────

export default function SummaryCard({ selectedMonth, refreshKey }) {
  // summary = the text Claude returns, or null if not loaded yet
  const [summary, setSummary] = useState(null)

  // loading = true while the API call is in flight
  const [loading, setLoading] = useState(false)

  // error = error message string if the call fails, or null
  const [error, setError] = useState(null)

  // ── Fetch summary whenever month or data changes ───────────────────
  // Dependencies: selectedMonth and refreshKey.
  //
  // refreshKey is passed down from Dashboard — it increments every
  // time the user uploads a new CSV. This means: after an upload,
  // the summary automatically refreshes to include the new transactions.
  //
  // Without refreshKey in the dependency array, the summary would
  // stay stale after an upload until the user manually changed the month.

  useEffect(() => {
    async function fetchSummary() {
      setLoading(true)
      setError(null)

      try {
        const { start_date, end_date } = getMonthRange(selectedMonth)

        // POST /api/summary — backend calls Claude and returns plain-English text
        const response = await api.post('/summary', { start_date, end_date })

        // response.data.summary is the string Claude generated
        setSummary(response.data.summary)

      } catch (err) {
        // err.response?.data?.detail is FastAPI's error message format
        // If that's not there, fall back to a generic message
        setError(err.response?.data?.detail || 'Could not load summary.')
      } finally {
        // Always set loading false, whether success or failure
        setLoading(false)
      }
    }

    fetchSummary()
  }, [selectedMonth, refreshKey])
  // ↑ Re-run when month changes OR when a new upload happens

  // ── Format the month for display ──────────────────────────────────
  // "2026-03" → "March 2026"
  const periodLabel = new Date(selectedMonth + '-01').toLocaleDateString('en-GB', {
    month: 'long', year: 'numeric',
  })

  // ── Render ─────────────────────────────────────────────────────────
  return (
    <div
      className="bg-white rounded-[14px] overflow-hidden flex-shrink-0"
      style={{ border: '1px solid #e8ecf4' }}
    >
      {/* Card header */}
      <div
        className="px-[18px] py-3.5 flex items-center justify-between"
        style={{ borderBottom: '1px solid #f0f3f9' }}
      >
        <span className="text-[13px] font-semibold" style={{ color: '#0f1c3f' }}>
          Summary
        </span>
        <span className="text-[11px]" style={{ color: '#9ca3af' }}>
          {periodLabel}
        </span>
      </div>

      {/* Card body */}
      <div className="px-[18px] py-3.5">
        {loading && <SummarySkeleton />}

        {error && !loading && (
          <p className="text-[12px]" style={{ color: '#dc2626' }}>
            {error}
          </p>
        )}

        {summary && !loading && (
          // Summary text from Claude.
          // leading-[1.75] = line height 1.75 — makes text comfortable to read.
          // whitespace-pre-wrap = respects any newlines Claude puts in the text.
          <p
            className="text-[12.5px] leading-[1.75] whitespace-pre-wrap"
            style={{ color: '#4b5563' }}
          >
            {summary}
          </p>
        )}

        {!summary && !loading && !error && (
          <p className="text-[12px]" style={{ color: '#9ca3af' }}>
            No transactions found for this period.
          </p>
        )}
      </div>
    </div>
  )
}