import { useState } from 'react'
import AppShell from '../components/layout/AppShell'
import Sidebar from '../components/layout/Sidebar'
import Topbar from '../components/layout/Topbar'
import KPIRow from '../components/dashboard/KPIRow'
import { TransactionPanel } from '../components/dashboard/TransactionPanel'
import api from '../lib/api'
import SummaryCard from '../components/dashboard/SummaryCard'
import QAChat from '../components/dashboard/QAChat'

export default function Dashboard() {

  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState(null)
  const [uploadError, setUploadError] = useState(null)

  const [selectedMonth, setSelectedMonth] = useState(() => {
    const now = new Date()
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  })

  // refreshKey increments after every upload
  // TransactionPanel watches this and re-fetches when it changes
  const [refreshKey, setRefreshKey] = useState(0)

  const selectedMonthDisplay = new Date(selectedMonth + '-01').toLocaleDateString('en-GB', {
    month: 'long', year: 'numeric',
  })

  // ── Upload handler ────────────────────────────────────────────
  async function handleUpload(event) {
    const file = event.target.files[0]
    if (!file) return

    setUploadResult(null)
    setUploadError(null)
    setUploading(true)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await api.post('/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })

      setUploadResult(response.data)
      // Increment refreshKey → TransactionPanel's useEffect re-runs
      // → fresh transactions load showing the new upload
      setRefreshKey(prev => prev + 1)

    } catch (error) {
      const message = error.response?.data?.detail || 'Upload failed. Please try again.'
      setUploadError(message)
    } finally {
      setUploading(false)
      event.target.value = ''
    }
  }

  // ── Export handler (Day 15) ───────────────────────────────────
  async function handleExport() {
    try {
      const response = await api.get('/report/pdf', { responseType: 'blob' })
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

  // ── Render ────────────────────────────────────────────────────
  return (
    <AppShell>
      <Sidebar />

      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
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

        <main className="flex-1 overflow-y-auto p-5 space-y-4">

          {/* Upload success banner */}
          {uploadResult && (
            <div
              className="rounded-[10px] px-4 py-3 flex items-center justify-between"
              style={{ background: '#ecfdf5', border: '1px solid #a7f3d0' }}
            >
              <div className="flex items-center gap-2.5">
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
              <button onClick={() => setUploadResult(null)}
                className="text-[18px] leading-none" style={{ color: '#059669' }}>×</button>
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
              <button onClick={() => setUploadError(null)}
                className="text-[18px] leading-none" style={{ color: '#dc2626' }}>×</button>
            </div>
          )}

          {/* KPI cards */}
          <KPIRow selectedMonth={selectedMonth} refreshKey={refreshKey} />

          {/* Two-column layout */}
          {/* 1fr = transaction table takes all available space */}
          {/* 300px = right column is fixed width */}
          <div
            className="grid gap-4"
            style={{ gridTemplateColumns: '1fr 300px' }}
          >

            {/* Left: Transaction table — live data */}
            <TransactionPanel
              selectedMonth={selectedMonth}
              refreshKey={refreshKey}
            />

            {/* Right: Summary + QA Chat */}
<div className="flex flex-col gap-3">
  <SummaryCard
    selectedMonth={selectedMonth}
    refreshKey={refreshKey}
  />
  <QAChat selectedMonth={selectedMonth} />
</div>
          </div>

        </main>
      </div>
    </AppShell>
  )
}