import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import AppShell from '../components/layout/AppShell'
import Sidebar from '../components/layout/Sidebar'
import Topbar from '../components/layout/Topbar'
import KPIRow from '../components/dashboard/KPIRow'
import api from '../lib/api'

export default function Dashboard() {
  const navigate = useNavigate()

  // uploading = true while the CSV is being sent to the backend
  const [uploading, setUploading] = useState(false)

  // uploadResult = the response from the backend after upload
  // { new_count, duplicate_count, anomalies_found, message }
  const [uploadResult, setUploadResult] = useState(null)

  // uploadError = error message string if upload fails
  const [uploadError, setUploadError] = useState(null)

  // selectedMonth = "2026-03" format — controls which month KPIs show
  // Default to current month
  const [selectedMonth, setSelectedMonth] = useState(() => {
    const now = new Date()
    // Pad month with leading zero: month 3 → "03"
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  })

  const [refreshKey, setRefreshKey] = useState(0)

  // Format selectedMonth for display: "2026-03" → "March 2026"
  const selectedMonthDisplay = new Date(selectedMonth + '-01').toLocaleDateString('en-GB', {
    month: 'long',
    year: 'numeric',
  })

  // ── Upload handler ────────────────────────────────────────────────
  // Called when user picks a file from the file picker
  async function handleUpload(event) {
    // event.target.files is a FileList — we take the first file
    const file = event.target.files[0]
    if (!file) return

    // Reset previous results
    setUploadResult(null)
    setUploadError(null)
    setUploading(true)

    try {
      // FormData is how you send files over HTTP
      // It creates a multipart/form-data request — the standard way
      // browsers send file uploads to servers
      const formData = new FormData()
      // 'file' must match the parameter name in your FastAPI endpoint:
      // async def upload_file(file: UploadFile = File(...))
      formData.append('file', file)

      const response = await api.post('/upload', formData, {
        headers: {
          // Tell the server this is a file upload, not JSON
          // axios sets this automatically with FormData, but being explicit is good
          'Content-Type': 'multipart/form-data',
        },
      })

      setUploadResult(response.data)
      setRefreshKey(prev => prev + 1)
    } catch (error) {
      // error.response.data.detail = FastAPI's error message
      const message = error.response?.data?.detail || 'Upload failed. Please try again.'
      setUploadError(message)
    } finally {
      setUploading(false)
      // Reset the file input so the same file can be re-uploaded if needed
      // Without this, selecting the same file again wouldn't trigger onChange
      event.target.value = ''
    }
  }

  // ── Export handler (stub for Day 15) ─────────────────────────────
  async function handleExport() {
    try {
      const response = await api.get('/report/pdf', {
        responseType: 'blob', // tell axios to treat response as binary file
      })
      // Create a temporary download link
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `fincopilot-${selectedMonth}.pdf`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch {
      alert('PDF export coming on Day 15')
    }
  }

  // ── Render ────────────────────────────────────────────────────────
  return (
    <AppShell>
      {/* Left: permanent sidebar */}
      <Sidebar />

      {/* Right: everything else — topbar + scrollable content */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">

        {/* Topbar — fixed at top of content area */}
        <Topbar
  title="Dashboard"
  selectedMonth={selectedMonthDisplay}
  onUpload={handleUpload}
  onExport={handleExport}
  uploading={uploading}
  onPrevMonth={() => {
    const [y, m] = selectedMonth.split('-').map(Number)
    const d = new Date(y, m - 2)
    setSelectedMonth(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`)
  }}
  onNextMonth={() => {
    const [y, m] = selectedMonth.split('-').map(Number)
    const d = new Date(y, m)
    setSelectedMonth(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`)
  }}
/>

        {/* Scrollable page content */}
        <main className="flex-1 overflow-y-auto p-5 space-y-4">

          {/* Upload result banner — shown after a successful upload */}
          {uploadResult && (
            <div
              className="rounded-[10px] px-4 py-3 flex items-center justify-between"
              style={{ background: '#ecfdf5', border: '1px solid #a7f3d0' }}
            >
              <div className="flex items-center gap-2.5">
                {/* Green tick */}
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <circle cx="8" cy="8" r="7" fill="#059669" />
                  <path d="M5 8l2 2 4-4" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
                <span className="text-[13px] font-medium" style={{ color: '#065f46' }}>
                  {uploadResult.new_count} new transactions added
                  {uploadResult.duplicate_count > 0 && ` · ${uploadResult.duplicate_count} duplicates skipped`}
                  {uploadResult.anomalies_found > 0 && ` · ${uploadResult.anomalies_found} anomalies detected`}
                </span>
              </div>
              {/* Dismiss button */}
              <button
                onClick={() => setUploadResult(null)}
                className="text-[18px] leading-none"
                style={{ color: '#059669' }}
              >
                ×
              </button>
            </div>
          )}

          {/* Upload error banner */}
          {uploadError && (
            <div
              className="rounded-[10px] px-4 py-3 flex items-center justify-between"
              style={{ background: '#fef2f2', border: '1px solid #fecaca' }}
            >
              <div className="flex items-center gap-2.5">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <circle cx="8" cy="8" r="7" fill="#dc2626" />
                  <path d="M5 5l6 6M11 5l-6 6" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
                <span className="text-[13px] font-medium" style={{ color: '#991b1b' }}>
                  {uploadError}
                </span>
              </div>
              <button
                onClick={() => setUploadError(null)}
                className="text-[18px] leading-none"
                style={{ color: '#dc2626' }}
              >
                ×
              </button>
            </div>
          )}

          {/* KPI cards row */}
          <KPIRow selectedMonth={selectedMonth} refreshKey={refreshKey} />

          {/* 
            Placeholder for Days 12-14 panels
            TransactionPanel + RightColumn go here
          */}
          <div
            className="rounded-[14px] flex items-center justify-center"
            style={{
              height: 300,
              border: '2px dashed #e8ecf4',
              color: '#9ca3af',
              fontSize: 13,
            }}
          >
            Transaction table + Summary + Q&amp;A — coming Days 12 &amp; 13
          </div>

        </main>
      </div>
    </AppShell>
  )
}