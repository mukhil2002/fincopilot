// ForecastChart.jsx
// Displays a line chart of historical + projected monthly financials
// Historical = solid line (real data)
// Projected = dashed line (AI forecast)
// Claude's narrative paragraph displayed below the chart
// Calls GET /api/forecast on mount

import { useEffect, useState } from 'react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import api from '../../lib/api'

// ── Month formatter ───────────────────────────────────────────────
// Converts "2026-05" → "May 26"
function formatMonth(monthStr) {
  const [year, mon] = monthStr.split('-')
  return new Date(year, mon - 1).toLocaleDateString('en-GB', {
    month: 'short',
    year: '2-digit',
  })
}

// ── Currency formatter ────────────────────────────────────────────
// Converts 24425 → "£24k" for axis labels (short form)
function formatGBPShort(value) {
  if (Math.abs(value) >= 1000) {
    return `£${(value / 1000).toFixed(0)}k`
  }
  return `£${value}`
}

// ── Custom Tooltip ────────────────────────────────────────────────
// The popup that appears when you hover over a data point
// Shows month + all three values formatted nicely
function CustomTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null

  return (
    <div
      className="rounded-xl px-4 py-3 text-[12px]"
      style={{
        background: '#fff',
        border: '1px solid #e8ecf4',
        boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
      }}
    >
      <p className="font-semibold mb-2" style={{ color: '#0f1c3f' }}>{label}</p>
      {payload.map(entry => (
        <div key={entry.name} className="flex items-center gap-2 mb-1">
          <span
            className="w-2 h-2 rounded-full flex-shrink-0"
            style={{ background: entry.color }}
          />
          <span style={{ color: '#6b7280' }}>{entry.name}:</span>
          <span className="font-medium" style={{ color: '#0f1c3f' }}>
            £{Math.abs(entry.value).toLocaleString('en-GB')}
          </span>
        </div>
      ))}
    </div>
  )
}

// ── Main Component ────────────────────────────────────────────────
export default function ForecastChart() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function fetchForecast() {
      try {
        const response = await api.get('/forecast')
        setData(response.data)
      } catch (err) {
        setError('Could not load forecast')
      } finally {
        setLoading(false)
      }
    }
    fetchForecast()
  }, [])

  // ── Loading state ─────────────────────────────────────────────
  if (loading) {
    return (
      <div
        className="bg-white rounded-[14px] p-5"
        style={{ border: '1px solid #e8ecf4' }}
      >
        <div className="h-4 rounded-full animate-pulse mb-4"
             style={{ background: '#f0f3f9', width: '30%' }} />
        <div className="h-48 rounded-xl animate-pulse"
             style={{ background: '#f0f3f9' }} />
      </div>
    )
  }

  // ── Error state ───────────────────────────────────────────────
  if (error) {
    return (
      <div
        className="bg-white rounded-[14px] p-5 text-center"
        style={{ border: '1px solid #e8ecf4' }}
      >
        <p className="text-[13px]" style={{ color: '#9ca3af' }}>{error}</p>
      </div>
    )
  }

  // ── Combine historical + projected into one array for Recharts ──
  // Recharts needs a single flat array to draw the chart
  // We mark projected rows with isProjected: true
  // This lets us use different line styles for each
  // Get the last historical point
const lastHistorical = data.historical[data.historical.length - 1]

const chartData = [
  ...data.historical.map(d => ({
    month: formatMonth(d.month),
    Revenue: d.revenue,
    Expenses: Math.abs(d.expenses),
    Profit: d.profit,
  })),
  // Repeat the last historical point as first projected point
  // This creates a visual connection between solid and dashed lines
  {
    month: formatMonth(lastHistorical.month),
    'Revenue (proj)': lastHistorical.revenue,
    'Expenses (proj)': Math.abs(lastHistorical.expenses),
    'Profit (proj)': lastHistorical.profit,
  },
  ...data.projected.map(d => ({
    month: formatMonth(d.month),
    'Revenue (proj)': d.revenue,
    'Expenses (proj)': Math.abs(d.expenses),
    'Profit (proj)': d.profit,
  })),
]

  return (
    <div
      className="bg-white rounded-[14px] overflow-hidden"
      style={{ border: '1px solid #e8ecf4' }}
    >
      {/* ── Header ─────────────────────────────────────────────── */}
      <div
        className="px-[18px] py-3.5 flex items-center justify-between"
        style={{ borderBottom: '1px solid #f0f3f9' }}
      >
        <span className="text-[13px] font-semibold" style={{ color: '#0f1c3f' }}>
          Cash Flow Forecast
        </span>
        <span className="text-[11px]" style={{ color: '#9ca3af' }}>
          {data.months_of_data} months of data · 3-month projection
        </span>
      </div>

      {/* ── Chart ──────────────────────────────────────────────── */}
      <div className="px-4 pt-4 pb-2">
        {/* ResponsiveContainer makes the chart fill its parent width */}
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>

            <CartesianGrid strokeDasharray="3 3" stroke="#f0f3f9" />

            <XAxis
              dataKey="month"
              tick={{ fontSize: 11, fill: '#9ca3af' }}
              axisLine={false}
              tickLine={false}
            />

            <YAxis
              tickFormatter={formatGBPShort}
              tick={{ fontSize: 11, fill: '#9ca3af' }}
              axisLine={false}
              tickLine={false}
              width={48}
            />

            <Tooltip content={<CustomTooltip />} />

            <Legend
              wrapperStyle={{ fontSize: 11, paddingTop: 12 }}
            />

            {/* Historical lines — solid */}
            <Line
              type="monotone"
              dataKey="Revenue"
              stroke="#2563eb"
              strokeWidth={2}
              dot={{ r: 3, fill: '#2563eb' }}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="Expenses"
              stroke="#7c3aed"
              strokeWidth={2}
              dot={{ r: 3, fill: '#7c3aed' }}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="Profit"
              stroke="#059669"
              strokeWidth={2}
              dot={{ r: 3, fill: '#059669' }}
              connectNulls
            />

            {/* Projected lines — dashed */}
            <Line
              type="monotone"
              dataKey="Revenue (proj)"
              stroke="#2563eb"
              strokeWidth={2}
              strokeDasharray="5 5"   // this makes it dashed
              dot={{ r: 3, fill: '#2563eb' }}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="Expenses (proj)"
              stroke="#7c3aed"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={{ r: 3, fill: '#7c3aed' }}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="Profit (proj)"
              stroke="#059669"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={{ r: 3, fill: '#059669' }}
              connectNulls
            />

          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* ── Claude Narrative ────────────────────────────────────── */}
      {/* Plain text paragraph from Claude below the chart */}
      <div
        className="px-[18px] py-3.5 text-[12px] leading-relaxed"
        style={{
          color: '#4b5563',
          borderTop: '1px solid #f0f3f9',
        }}
      >
        {data.narrative}
      </div>

    </div>
  )
}