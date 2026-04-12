// FilterBar.jsx
// A row of clickable filter chips above the transaction table
// Controls which transactions are visible — filters happen in the browser
// No API call needed — we already have all transactions loaded

// ── Filter definitions ────────────────────────────────────────────
// Each filter has:
//   id    = internal key used in logic
//   label = what the user sees on the chip
//
// We define them here as a constant so the list is easy to change later
// If you want to add "Payroll" as a filter chip, just add one line here
export const FILTERS = [
    { id: 'all',            label: 'All' },
    { id: 'anomalies',      label: 'Anomalies' },
    { id: 'low_confidence', label: 'Low confidence' },
    { id: 'revenue',        label: 'Revenue' },
    { id: 'expenses',       label: 'Expenses' },
  ]
  
  // ── filterTransactions ────────────────────────────────────────────
  // Pure function — takes a list of transactions + active filter id
  // Returns only the transactions that match that filter
  //
  // "Pure function" means: same input always gives same output
  // No side effects, no API calls — just data in, data out
  // This makes it easy to test and reason about
  //
  // Called by TransactionPanel (Step 5) to filter before rendering rows
  export function filterTransactions(transactions, activeFilter) {
    switch (activeFilter) {
  
      case 'anomalies':
        // is_anomaly is a boolean — true means Claude or ML flagged it
        return transactions.filter(t => t.is_anomaly)
  
      case 'low_confidence':
        // Below 0.70 = red bar = needs review
        // Number() converts Decimal strings from the API to JS numbers
        return transactions.filter(t => Number(t.confidence) < 0.70)
  
      case 'revenue':
        // Positive amount = money coming IN = Revenue
        // amount comes as a string from Decimal — Number() converts it
        return transactions.filter(t => Number(t.amount) > 0)
  
      case 'expenses':
        // Negative amount = money going OUT = an expense
        return transactions.filter(t => Number(t.amount) < 0)
  
      case 'all':
      default:
        // Return everything — no filter applied
        return transactions
    }
  }
  
  // ── Component ─────────────────────────────────────────────────────
  // Props:
  //   activeFilter    = string — which filter is currently selected
  //                     e.g. 'all', 'anomalies', 'low_confidence'
  //   onFilterChange  = function — called with the new filter id
  //                     when user clicks a chip
  //   anomalyCount    = number — how many anomalies exist
  //                     shown as a small badge on the Anomalies chip
  //                     so the user sees "Anomalies 3" without clicking
  export function FilterBar({ activeFilter, onFilterChange, anomalyCount }) {
    return (
      // Horizontal row of chips with a bottom border separating from table
      <div
        className="flex gap-1.5 px-[18px] py-2.5 flex-wrap flex-shrink-0"
        style={{ borderBottom: '1px solid #f0f3f9' }}
      >
        {/* Loop over FILTERS array — one chip per filter */}
        {FILTERS.map(filter => {
  
          // Is this chip the currently active one?
          const isActive = activeFilter === filter.id
  
          return (
            <button
              key={filter.id}
              onClick={() => onFilterChange(filter.id)}
              className="text-[11px] font-medium px-3 py-1 rounded-full transition-all flex items-center gap-1.5"
  
              // Active chip = blue background + blue border + blue bold text
              // Inactive chip = white background + grey border + grey text
              style={
                isActive
                  ? {
                      background: '#eff4ff',
                      border: '1px solid #93c5fd',
                      color: '#2563eb',
                      fontWeight: 600,
                    }
                  : {
                      background: '#fff',
                      border: '1px solid #e5e7eb',
                      color: '#6b7280',
                    }
              }
            >
              {/* The chip label e.g. "All", "Anomalies" */}
              {filter.label}
  
              {/* Anomaly count badge — only shown on the Anomalies chip */}
              {/* and only when there are actually anomalies to show */}
              {filter.id === 'anomalies' && anomalyCount > 0 && (
                <span
                  className="text-[9px] font-semibold px-1.5 py-0.5 rounded-full"
                  style={{ background: '#fef3c7', color: '#d97706' }}
                >
                  {anomalyCount}
                </span>
              )}
            </button>
          )
        })}
      </div>
    )
  }