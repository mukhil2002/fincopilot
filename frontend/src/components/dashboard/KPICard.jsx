// KPICard.jsx
// Displays ONE metric — a label, a big number, and a delta line.
//
// Props:
//   label          = "Revenue", "Expenses", "Net Profit", "Anomalies"
//   value          = the formatted string to display e.g. "£12,400" or "3"
//   delta          = optional line below the number e.g. "↑ 8% vs February"
//   deltaType      = "up" | "down" | "warn" — controls delta text colour
//   accentGradient = CSS gradient string for the 3px top strip
//   loading        = boolean — show skeleton while data is fetching

export default function KPICard({ label, value, delta, deltaType, accentGradient, loading }) {

    // ── Loading skeleton ──────────────────────────────────────────────
    // While transactions are being fetched, show an animated placeholder.
    // This is called a skeleton screen — much better UX than a spinner
    // because the user can see the SHAPE of the content before it loads.
    // animate-pulse is a Tailwind class that fades in and out repeatedly.
    if (loading) {
      return (
        <div
          className="bg-white rounded-[14px] p-4 relative overflow-hidden"
          style={{ border: '1px solid #e8ecf4' }}
        >
          {/* Fake gradient strip — same position as real one */}
          <div
            className="absolute top-0 left-0 right-0 h-[3px] rounded-t-[14px] animate-pulse"
            style={{ background: '#e8ecf4' }}
          />
          {/* Fake label line */}
          <div
            className="h-2.5 rounded-full animate-pulse mb-3 mt-1"
            style={{ background: '#f0f3f9', width: '40%' }}
          />
          {/* Fake big number */}
          <div
            className="h-7 rounded-full animate-pulse"
            style={{ background: '#f0f3f9', width: '60%' }}
          />
          {/* Fake delta line */}
          <div
            className="h-2 rounded-full animate-pulse mt-2"
            style={{ background: '#f0f3f9', width: '50%' }}
          />
        </div>
      )
    }
  
    // ── Real card ─────────────────────────────────────────────────────
    return (
      <div
        className="bg-white rounded-[14px] p-4 relative overflow-hidden"
        style={{ border: '1px solid #e8ecf4' }}
      >
        {/*
          The 3px gradient strip at the very top of the card.
          absolute = positioned relative to the card (which has relative)
          top-0 left-0 right-0 = stretches full width along the top edge
          overflow-hidden on the parent clips it to the card's rounded corners
          
          Each of the 4 cards gets a different gradient colour:
          Revenue   → blue
          Expenses  → purple  
          Profit    → green
          Anomalies → amber
        */}
        <div
          className="absolute top-0 left-0 right-0 h-[3px] rounded-t-[14px]"
          style={{ background: accentGradient }}
        />
  
        {/*
          KPI label — small, uppercase, muted
          uppercase + tracking = design convention for data labels
          It signals "this is a category, not a value"
        */}
        <p
          className="text-[11px] font-medium uppercase tracking-[0.05em] mb-2"
          style={{ color: '#6b7280' }}
        >
          {label}
        </p>
  
        {/*
          The big number — the most important thing on the card
          deltaType === 'warn' means anomalies — shown in amber not navy
          because anomalies need attention, not celebration
        */}
        <p
          className="text-[24px] font-bold tracking-tight leading-none"
          style={{ color: deltaType === 'warn' ? '#d97706' : '#0f1c3f' }}
        >
          {value}
        </p>
  
        {/*
          Delta line — optional secondary context
          e.g. "↑ 8% vs February" or "29% margin"
          Colour is semantic:
            up   = emerald (good news — revenue went up)
            down = red     (bad news — expenses went up)
            warn = amber   (needs attention — anomalies)
        */}
        {delta && (
          <p
            className={`text-[11px] mt-1.5 flex items-center gap-1 ${
              deltaType === 'up'   ? 'text-emerald-600' :
              deltaType === 'down' ? 'text-red-500'     :
                                     'text-amber-500'
            }`}
          >
            {delta}
          </p>
        )}
      </div>
    )
  }