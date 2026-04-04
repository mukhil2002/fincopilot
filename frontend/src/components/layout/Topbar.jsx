// Topbar.jsx
// The white horizontal bar at the top of every page.
// Left: page title + month picker
// Right: Export PDF button + Upload CSV button
// 
// Props:
//   title         = page heading shown in the bar ("Dashboard")
//   selectedMonth = the currently selected period ("March 2026")
//   onUpload      = function called when user picks a CSV file
//   onExport      = function called when user clicks Export PDF
//   uploading     = boolean — true while CSV is being processed

export default function Topbar({ title, selectedMonth, onUpload, onExport, uploading,onPrevMonth, onNextMonth }) {
    return (
      <header
        className="bg-white h-14 px-6 flex items-center justify-between flex-shrink-0"
        style={{ borderBottom: '1px solid #e8ecf4' }}
      >
        {/* ── Left side: title + month picker ── */}
        <div className="flex items-center gap-3">
          <h1 className="text-[15px] font-semibold" style={{ color: '#0f1c3f' }}>
            {title}
          </h1>
  
          {/* Month picker button — visual only for now, full picker in Day 14 */}
          <div className="flex items-center gap-1">
  <button onClick={onPrevMonth} className="p-1 rounded hover:bg-gray-100" style={{ color: '#2563eb' }}>
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="9,2 4,7 9,12" />
    </svg>
  </button>
  <span
    className="flex items-center gap-1.5 text-[11px] font-medium rounded-full px-3 py-1"
    style={{ color: '#2563eb', background: '#eff4ff', border: '1px solid #bfdbfe' }}
  >
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5">
      <rect x="1" y="2" width="10" height="9" rx="1.5" />
      <line x1="1" y1="5" x2="11" y2="5" />
      <line x1="4" y1="1" x2="4" y2="3" />
      <line x1="8" y1="1" x2="8" y2="3" />
    </svg>
    {selectedMonth}
  </span>
  <button onClick={onNextMonth} className="p-1 rounded hover:bg-gray-100" style={{ color: '#2563eb' }}>
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="5,2 10,7 5,12" />
    </svg>
  </button>
</div>
        </div>
  
        {/* ── Right side: action buttons ── */}
        <div className="flex items-center gap-2.5">
  
          {/* Export PDF button */}
          <button
            onClick={onExport}
            className="flex items-center gap-1.5 text-[12px] font-medium px-3 py-[6px] rounded-lg transition-colors"
            style={{ color: '#4b5563', background: '#fff', border: '1px solid #e5e7eb' }}
            // Inline hover effect — we can't use Tailwind hover: for dynamic inline styles
            onMouseEnter={e => {
              e.currentTarget.style.borderColor = '#93c5fd'
              e.currentTarget.style.color = '#2563eb'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.borderColor = '#e5e7eb'
              e.currentTarget.style.color = '#4b5563'
            }}
          >
            {/* Download arrow icon */}
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M7 2v7M4 6l3 3 3-3" strokeLinecap="round" />
              <path d="M2 11h10" strokeLinecap="round" />
            </svg>
            Export PDF
          </button>
  
          {/*
            Upload CSV button.
            
            This is a <label> wrapping a hidden <input type="file">.
            Why? Because <input type="file"> is the only way to open
            the file picker dialog. But it's ugly by default.
            Wrapping it in a <label> means clicking the styled label
            triggers the hidden input — giving us a fully custom button.
            
            When uploading = true, we show a spinner instead of the button.
          */}
          {uploading ? (
            // Processing state — shown while CSV is being sent to backend
            <div className="flex items-center gap-2 text-[12px]" style={{ color: '#6b7280' }}>
              {/* Spinning circle */}
              <svg
                className="animate-spin"
                width="16" height="16" viewBox="0 0 16 16"
                fill="none" stroke="#2563eb" strokeWidth="2"
              >
                <circle cx="8" cy="8" r="6" strokeOpacity="0.2" />
                <path d="M8 2a6 6 0 0 1 6 6" strokeLinecap="round" />
              </svg>
              Processing...
            </div>
          ) : (
            // Default state
            <label
              className="flex items-center gap-1.5 text-[12px] font-semibold text-white px-3.5 py-[7px] rounded-lg cursor-pointer transition-colors"
              style={{
                background: '#2563eb',
                boxShadow: '0 1px 4px rgba(37,99,235,0.27)',
              }}
              onMouseEnter={e => { e.currentTarget.style.background = '#1d4ed8' }}
              onMouseLeave={e => { e.currentTarget.style.background = '#2563eb' }}
            >
              {/* Upload arrow icon */}
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M7 9V2M4 5l3-3 3 3" strokeLinecap="round" />
                <path d="M2 11h10" strokeLinecap="round" />
              </svg>
              Upload CSV
              {/*
                Hidden file input.
                accept=".csv,.pdf" limits the file picker to CSV and PDF files.
                onChange fires when user selects a file.
                className="hidden" makes it invisible — the label handles visuals.
              */}
              <input
                type="file"
                accept=".csv,.pdf"
                className="hidden"
                onChange={onUpload}
              />
            </label>
          )}
        </div>
      </header>
    )
  }