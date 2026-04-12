// TransactionPanel.jsx — FULL FILE REPLACE
// Added: correctingTxn state, handleCorrect, handleCategorySelect
// Added: renders CategoryDropdown when a badge is clicked
// TransactionPanel is now fully self-contained — Dashboard just passes props

import { useState, useEffect } from 'react'
import api from '../../lib/api'
import { FilterBar, filterTransactions } from './FilterBar'
import { TransactionRow } from './TransactionRow'
import { CategoryDropdown } from '../ui/CategoryDropdown'

// ── Loading skeleton ──────────────────────────────────────────────
function TableSkeleton() {
  return (
    <>
      {Array(6).fill(0).map((_, i) => (
        <tr key={i} style={{ borderBottom: '1px solid #f7f8fc' }}>
          {[48, 152, 72, 48, 44, 16].map((w, j) => (
            <td key={j} className="px-3.5 py-3">
              <div
                className="h-3 rounded-full animate-pulse"
                style={{ background: '#f0f3f9', width: w }}
              />
            </td>
          ))}
        </tr>
      ))}
    </>
  )
}

// ── Empty state ───────────────────────────────────────────────────
function EmptyState({ variant }) {
  const isNoData = variant === 'noData'
  return (
    <tr>
      <td colSpan={6}>
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <div
            className="w-12 h-12 rounded-2xl flex items-center justify-center mb-3"
            style={{ background: '#eff4ff' }}
          >
            {isNoData ? (
              <svg width="22" height="22" fill="none" viewBox="0 0 24 24"
                   stroke="#60a5fa" strokeWidth="1.8">
                <path strokeLinecap="round" strokeLinejoin="round"
                  d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
              </svg>
            ) : (
              <svg width="22" height="22" fill="none" viewBox="0 0 24 24"
                   stroke="#60a5fa" strokeWidth="1.8">
                <path strokeLinecap="round" strokeLinejoin="round"
                  d="M12 3c2.755 0 5.455.232 8.083.678.533.09.917.556.917 1.096v1.044a2.25 2.25 0 01-.659 1.591L15 12.75V21a.75.75 0 01-1.079.67l-4.5-2.25A.75.75 0 019 18.75v-6l-5.341-5.431A2.25 2.25 0 013 5.818V4.774c0-.54.384-1.006.917-1.096A48.32 48.32 0 0112 3z" />
              </svg>
            )}
          </div>
          <p className="text-[13px] font-semibold mb-1" style={{ color: '#0f1c3f' }}>
            {isNoData ? 'No transactions yet' : 'No matches'}
          </p>
          <p className="text-[11.5px] leading-relaxed" style={{ color: '#9ca3af', maxWidth: 200 }}>
            {isNoData
              ? 'Upload a bank statement CSV to get started'
              : 'No transactions match this filter'}
          </p>
        </div>
      </td>
    </tr>
  )
}

// ── Main Component ────────────────────────────────────────────────
// Props:
//   selectedMonth = "2026-03"
//   refreshKey    = increments after upload → triggers re-fetch
export function TransactionPanel({ selectedMonth, refreshKey }) {

  const [transactions, setTransactions] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeFilter, setActiveFilter] = useState('all')
  const [total, setTotal] = useState(0)

  // ── Dropdown state ────────────────────────────────────────────
  // correctingTxn = the transaction object whose category is being changed
  // null = dropdown is closed
  const [correctingTxn, setCorrectingTxn] = useState(null)

  // dropdownPosition = { top, left } in pixels
  // calculated from where the badge was clicked on screen
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0 })

  // ── Fetch transactions ────────────────────────────────────────
  useEffect(() => {
    async function fetchTransactions() {
      setLoading(true)
      try {
        const response = await api.get('/transactions', {
          params: { month: selectedMonth, per_page: 100 },
        })
        setTransactions(response.data.transactions)
        setTotal(response.data.total)
      } catch (error) {
        console.error('Failed to fetch transactions:', error)
        setTransactions([])
        setTotal(0)
      } finally {
        setLoading(false)
      }
    }
    fetchTransactions()
  }, [selectedMonth, refreshKey])

  // ── Handle badge / pencil click ───────────────────────────────
  // Called by TransactionRow when user clicks a badge or pencil
  // txn   = the transaction object
  // event = the mouse click event — we use this to find screen position
  function handleCorrect(txn, event) {

    // getBoundingClientRect() returns the size and position of
    // the clicked element relative to the viewport (the screen)
    // e.g. { top: 340, bottom: 360, left: 450, right: 550 }
    const rect = event.currentTarget.getBoundingClientRect()

    // Position the dropdown just below the clicked element
    // + 6px gap so it doesn't sit flush against the badge
    setDropdownPosition({
      top: rect.bottom + 6,
      left: rect.left,
    })

    // Store which transaction we're correcting
    setCorrectingTxn(txn)
  }

  // ── Handle category selection ─────────────────────────────────
  // Called by CategoryDropdown when user picks a new category
  // Optimistic update: change the badge immediately, don't wait for API
  function handleCategorySelect(txnId, newCategory) {

    // map() creates a new array — never mutate state directly in React
    // For every transaction: if it's the one being corrected, update
    // its category. Otherwise return it unchanged.
    setTransactions(prev =>
      prev.map(t =>
        t.id === txnId
          ? { ...t, category: newCategory, confidence: 1.0 }
          : t
        // { ...t } = spread operator = copy all existing fields
        // then override category and confidence
        // confidence: 1.0 because human confirmed = full trust
      )
    )
  }

  // ── Derived values ────────────────────────────────────────────
  const filtered = filterTransactions(transactions, activeFilter)
  const anomalyCount = transactions.filter(t => t.is_anomaly).length
  const monthDisplay = new Date(selectedMonth + '-01').toLocaleDateString('en-GB', {
    month: 'long', year: 'numeric',
  })

  // ── Render ────────────────────────────────────────────────────
  return (
    // Fragment = wrapper that renders nothing in the DOM
    // We need this because we're rendering both the card AND
    // the dropdown (which floats outside the card via fixed positioning)
    <>
      <div
        className="bg-white rounded-[14px] overflow-hidden flex flex-col"
        style={{ border: '1px solid #e8ecf4' }}
      >

        {/* Card header */}
        <div
          className="px-[18px] py-3.5 flex items-center justify-between flex-shrink-0"
          style={{ borderBottom: '1px solid #f0f3f9' }}
        >
          <span className="text-[13px] font-semibold" style={{ color: '#0f1c3f' }}>
            Transactions
          </span>
          <span className="text-[11px]" style={{ color: '#9ca3af' }}>
            {loading ? 'Loading...' : `${total} total · ${monthDisplay}`}
          </span>
        </div>

        {/* Filter chips */}
        <div className="flex-shrink-0">
          <FilterBar
            activeFilter={activeFilter}
            onFilterChange={setActiveFilter}
            anomalyCount={anomalyCount}
          />
        </div>

        {/* Scrollable table */}
        <div className="flex-1 overflow-y-auto" style={{ maxHeight: 380 }}>
          <table className="w-full border-collapse">

            <thead className="sticky top-0 z-10" style={{ background: '#fafbfd' }}>
              <tr>
                {['Date', 'Description', 'Category', 'Amount', 'Confidence', ''].map(col => (
                  <th
                    key={col}
                    className="px-3.5 py-2.5 text-left text-[10.5px] font-semibold uppercase tracking-[0.05em]"
                    style={{
                      color: '#9ca3af',
                      borderBottom: '1px solid #f0f3f9',
                      textAlign: col === 'Amount' ? 'right' : 'left',
                      width: col === 'Description' ? '35%' : 'auto',
                    }}
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>

            <tbody>
              {loading ? (
                <TableSkeleton />
              ) : filtered.length === 0 ? (
                <EmptyState variant={transactions.length === 0 ? 'noData' : 'noMatches'} />
              ) : (
                filtered.map(txn => (
                  <TransactionRow
                    key={txn.id}
                    txn={txn}
                    onCorrect={handleCorrect}
                  />
                ))
              )}
            </tbody>

          </table>
        </div>
      </div>

      {/* Dropdown — rendered outside the card but inside the Fragment */}
      {/* Only rendered when correctingTxn is not null */}
      {/* fixed positioning means it floats above everything else */}
      {correctingTxn && (
        <CategoryDropdown
          txn={correctingTxn}
          position={dropdownPosition}
          onSelect={handleCategorySelect}
          onClose={() => setCorrectingTxn(null)}
        />
      )}
    </>
  )
}