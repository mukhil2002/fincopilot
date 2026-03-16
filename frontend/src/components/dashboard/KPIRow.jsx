// KPIRow.jsx
// Fetches all transactions, calculates the four KPI values,
// and renders four KPICard components in a grid row.
//
// This component owns the data-fetching responsibility for KPIs.
// KPICard is purely for display — it knows nothing about the API.
//
// Props:
//   selectedMonth = "2026-03" — used to filter transactions to this month

import { useState, useEffect } from 'react'
import KPICard from './KPICard'
import api from '../../lib/api'

// ── Helpers ──────────────────────────────────────────────────────────────────

// Format a number as GBP currency
// 12400    → "£12,400"
// 8750.50  → "£8,751"  (rounded, no decimals for KPI display)
function formatGBP(amount) {
  if (!amount || isNaN(amount)) return '£0'
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'GBP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(Math.abs(amount))
}

// The four card configurations
// Each defines the static parts — label, gradient, deltaType
// The dynamic parts (value, delta) are calculated from real data below
const CARD_CONFIG = [
  {
    key: 'revenue',
    label: 'Revenue',
    deltaType: 'up',
    accentGradient: 'linear-gradient(90deg, #2563eb, #60a5fa)',
  },
  {
    key: 'expenses',
    label: 'Expenses',
    deltaType: 'down',
    accentGradient: 'linear-gradient(90deg, #7c3aed, #a78bfa)',
  },
  {
    key: 'profit',
    label: 'Net Profit',
    deltaType: 'up',
    accentGradient: 'linear-gradient(90deg, #059669, #34d399)',
  },
  {
    key: 'anomalies',
    label: 'Anomalies',
    deltaType: 'warn',
    accentGradient: 'linear-gradient(90deg, #d97706, #fbbf24)',
  },
]

// ── KPIRow ───────────────────────────────────────────────────────────────────

export default function KPIRow({ selectedMonth, refreshKey }) {
  // transactions = the raw array from the API
  // null means "not fetched yet" — distinct from [] which means "fetched, none found"
  const [transactions, setTransactions] = useState(null)

  // loading = true while the API call is in flight
  const [loading, setLoading] = useState(true)

  // ── Data fetching ─────────────────────────────────────────────────
  useEffect(() => {
    async function fetchTransactions() {
      setLoading(true)
      try {
        // GET /api/transactions returns all transactions for this user
        // The api instance automatically attaches the JWT token (from api.js)
        const response = await api.get('/transactions', {
          params: {
            // Send selectedMonth as a query parameter so backend can filter
            // e.g. /api/transactions?month=2026-03
            // If your backend doesn't support month filtering yet,
            // we filter client-side below — both approaches are handled
            limit: 500, // fetch up to 500 transactions
          }
        })

        // response.data is what FastAPI returned
        // Your backend returns { transactions: [...], total: N }
        // or just an array — we handle both shapes
        const data = response.data
        const txns = data.transactions || []
        setTransactions(txns)
      } catch (error) {
        console.error('Failed to fetch transactions:', error)
        // On error, set empty array so the UI shows £0 rather than loading forever
        setTransactions([])
      } finally {
        // finally runs whether the try succeeded or the catch fired
        // Always stop the loading spinner
        setLoading(false)
      }
    }

    fetchTransactions()
  }, [selectedMonth, refreshKey]) // re-fetch when month changes

  // ── Calculate KPI values from raw transactions ────────────────────
  // This runs every render but only after transactions are loaded.
  // We filter to the selected month first, then sum.
  
  const filtered = (transactions || []).filter(txn => {
    if (!selectedMonth) return true
    // txn.txn_date is "2026-03-14" — we take the first 7 chars "2026-03"
    return txn.txn_date?.startsWith(selectedMonth)
  })

  // Revenue = sum of all POSITIVE amounts (money coming in)
  const revenue = filtered
    .filter(t => parseFloat(t.amount) > 0)
    .reduce((sum, t) => sum + parseFloat(t.amount), 0)
  // Expenses = sum of all NEGATIVE amounts (money going out)
  // We store them as negative numbers in the DB, so we use Math.abs
  // to show the user a positive number (e.g. "£8,750" not "-£8,750")
  const expenses = filtered
    .filter(t => parseFloat(t.amount) < 0)
    .reduce((sum, t) => sum + Math.abs(parseFloat(t.amount)), 0)

  // Profit = Revenue minus Expenses
  const profit = revenue - expenses

  // Margin = profit as a percentage of revenue
  // Guard against division by zero when revenue = 0
  const margin = revenue > 0 ? Math.round((profit / revenue) * 100) : 0

  // Anomaly count = transactions flagged by ML
  const anomalyCount = filtered.filter(t => t.is_anomaly).length

  // ── Build card data ───────────────────────────────────────────────
  // Map each card config to its dynamic values
  const cardData = {
    revenue: {
      value: formatGBP(revenue),
      delta: revenue > 0 ? `↑ This month` : 'No revenue yet',
    },
    expenses: {
      value: formatGBP(expenses),
      delta: expenses > 0 ? `↑ Total outgoings` : 'No expenses yet',
    },
    profit: {
      value: formatGBP(profit),
      delta: revenue > 0 ? `${margin}% margin` : 'Upload data to see margin',
    },
    anomalies: {
      value: String(anomalyCount),
      delta: anomalyCount > 0 ? `${anomalyCount} need review` : 'Nothing flagged',
    },
  }

  // ── Render ────────────────────────────────────────────────────────
  return (
    // grid-cols-4 = 4 equal columns
    // gap-3 = 12px gap between cards
    <div className="grid grid-cols-4 gap-3">
      {CARD_CONFIG.map(config => (
        <KPICard
          key={config.key}
          label={config.label}
          value={cardData[config.key].value}
          delta={cardData[config.key].delta}
          deltaType={config.deltaType}
          accentGradient={config.accentGradient}
          loading={loading}
        />
      ))}
    </div>
  )
}