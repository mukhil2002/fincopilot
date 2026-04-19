// Topbar.jsx
// The white horizontal bar at the top of every page.
// Left: page title + month picker
// Right: Export PDF button + Upload CSV button
//
// Props:
//   title         = page heading shown in the bar ("Dashboard")
//   selectedMonth = the currently selected period ("March 2026")
//   onUpload      = function called when user picks a CSV file
//   uploading     = boolean — true while CSV is being processed
//   onPrevMonth   = function called when user clicks ← arrow
//   onNextMonth   = function called when user clicks → arrow
//
// Note: onExport is REMOVED — export logic now lives inside this
// component so it can access the api instance directly.

import api from '../../lib/api'

export default function Topbar({ title, selectedMonth, onUpload, uploading, onPrevMonth, onNextMonth }) {

  // Converts "March 2026" → "2026-03" for the API query parameter
  // The backend expects YYYY-MM format
  function parseMonthParam(label) {
    const months = {
      'January':   '01', 'February': '02', 'March':    '03',
      'April':     '04', 'May':       '05', 'June':     '06',
      'July':      '07', 'August':    '08', 'September':'09',
      'October':   '10', 'November':  '11', 'December': '12',
    }
    // "March 2026" → ["March", "2026"]
    const parts = label.split(' ')
    const month = months[parts[0]]
    const year  = parts[1]
    return `${year}-${month}`  // → "2026-03"
  }

  async function handleExport() {
    try {
      const monthParam = parseMonthParam(selectedMonth)

      // responseType: 'blob' is critical here.
      // Normally Axios tries to parse responses as JSON or text.
      // A PDF is raw binary — if Axios tries to decode it as text,
      // the bytes get corrupted and the PDF becomes unreadable.
      // 'blob' tells Axios: hand me the raw bytes, don't touch them.
      const response = await api.get(`/report/pdf?month=${monthParam}`, {
        responseType: 'blob',
      })

      // URL.createObjectURL() takes a Blob (raw binary data)
      // and creates a temporary URL that only exists in this browser tab.
      // It looks like: blob:http://localhost:5173/abc-123-def
      // The browser can use this URL to access the data in memory.
      const url = URL.createObjectURL(response.data)

      // We can't trigger a file download by just navigating to a URL.
      // The standard trick: create a hidden <a> tag, set its href
      // to our blob URL, set the filename via the download attribute,
      // then click it programmatically. The browser treats this exactly
      // like the user clicking a download link.
      const link = document.createElement('a')
      link.href = url
      link.download = `fincopilot-${monthParam}.pdf`
      document.body.appendChild(link)
      link.click()

      // Clean up immediately after the click.
      // removeChild removes the invisible <a> tag from the DOM.
      // revokeObjectURL frees the memory the blob was using.
      // If we don't do this, the memory leaks for the lifetime of the tab.
      document.body.removeChild(link)
      URL.revokeObjectURL(url)

    } catch (err) {
      console.error('PDF export failed:', err)
      alert('Failed to generate report. Please try again.')
    }
  }

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

        {/* Export PDF button — calls handleExport defined above */}
        <button
          onClick={handleExport}
          className="flex items-center gap-1.5 text-[12px] font-medium px-3 py-[6px] rounded-lg transition-colors"
          style={{ color: '#4b5563', background: '#fff', border: '1px solid #e5e7eb' }}
          onMouseEnter={e => {
            e.currentTarget.style.borderColor = '#93c5fd'
            e.currentTarget.style.color = '#2563eb'
          }}
          onMouseLeave={e => {
            e.currentTarget.style.borderColor = '#e5e7eb'
            e.currentTarget.style.color = '#4b5563'
          }}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M7 2v7M4 6l3 3 3-3" strokeLinecap="round" />
            <path d="M2 11h10" strokeLinecap="round" />
          </svg>
          Export PDF
        </button>

        {/* Upload CSV button — unchanged from Day 11 */}
        {uploading ? (
          <div className="flex items-center gap-2 text-[12px]" style={{ color: '#6b7280' }}>
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
          <label
            className="flex items-center gap-1.5 text-[12px] font-semibold text-white px-3.5 py-[7px] rounded-lg cursor-pointer transition-colors"
            style={{
              background: '#2563eb',
              boxShadow: '0 1px 4px rgba(37,99,235,0.27)',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = '#1d4ed8' }}
            onMouseLeave={e => { e.currentTarget.style.background = '#2563eb' }}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M7 9V2M4 5l3-3 3 3" strokeLinecap="round" />
              <path d="M2 11h10" strokeLinecap="round" />
            </svg>
            Upload CSV
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