import { useState, useEffect, useRef } from 'react'
import api from '../../lib/api'

// ── Helper: same as SummaryCard ────────────────────────────────────────
// Turns "2026-03" into { start_date: "2026-03-01", end_date: "2026-03-31" }
// We send these with every question so Claude only looks at the
// selected month's transactions, not all transactions ever.

function getMonthRange(yearMonth) {
  const [year, month] = yearMonth.split('-').map(Number)
  const firstDay = `${yearMonth}-01`
  const lastDay = new Date(year, month, 0).getDate()
  const endDate = `${yearMonth}-${String(lastDay).padStart(2, '0')}`
  return { start_date: firstDay, end_date: endDate }
}

// ── Suggested questions ────────────────────────────────────────────────
// Shown when the chat is empty.
// Tapping one fills the input — user can send immediately.
// Helps users who don't know what to ask.

const SUGGESTIONS = [
  "What is my biggest expense this month?",
  "How much did I spend on payroll?",
  "How many anomalies were flagged?",
  "What was my profit margin?",
]

function SuggestedQuestions({ onSelect }) {
  return (
    <div className="space-y-1.5 p-1">
      <p className="text-[10.5px] mb-2" style={{ color: '#9ca3af' }}>
        Try asking...
      </p>
      {SUGGESTIONS.map((q) => (
        <button
          key={q}
          onClick={() => onSelect(q)}
          className="w-full text-left text-[11.5px] px-3 py-2 rounded-lg transition-all"
          style={{
            color: '#4b5563',
            background: '#f4f6fb',
            border: '1px solid #e8ecf4',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = '#eff4ff'
            e.currentTarget.style.borderColor = '#bfdbfe'
            e.currentTarget.style.color = '#2563eb'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = '#f4f6fb'
            e.currentTarget.style.borderColor = '#e8ecf4'
            e.currentTarget.style.color = '#4b5563'
          }}
        >
          {q}
        </button>
      ))}
    </div>
  )
}

// ── Typing indicator ───────────────────────────────────────────────────
// Three bouncing dots shown while Claude is thinking.
// animationDelay staggers them so they bounce one after another,
// not all at the same time.

function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div
        className="px-3 py-2.5"
        style={{
          background: '#f4f6fb',
          border: '1px solid #e8ecf4',
          borderRadius: '3px 14px 14px 14px',
        }}
      >
        <div className="flex gap-1 items-center h-4">
          {[0, 150, 300].map((delay) => (
            <span
              key={delay}
              className="w-1.5 h-1.5 rounded-full animate-bounce"
              style={{ background: '#60a5fa', animationDelay: `${delay}ms` }}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Chat bubble ────────────────────────────────────────────────────────
// User messages: blue background, right side, rounded top-left corner flat
// AI messages: grey background, left side, rounded top-right corner flat
//
// The asymmetric border radius is what makes it look like a real chat app.
// isUser=true  → "14px 14px 3px 14px" (bottom-left is flat)
// isUser=false → "3px 14px 14px 14px" (top-left is flat)

function ChatBubble({ message }) {
  const isUser = message.role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className="text-[12px] leading-snug px-3 py-2 max-w-[90%]"
        style={{
          background: isUser ? '#2563eb' : '#f4f6fb',
          color: isUser ? '#ffffff' : '#1f2937',
          border: isUser ? 'none' : '1px solid #e8ecf4',
          borderRadius: isUser
            ? '14px 14px 3px 14px'
            : '3px 14px 14px 14px',
        }}
      >
        {message.text}
      </div>
    </div>
  )
}

// ── Main component ─────────────────────────────────────────────────────

export default function QAChat({ selectedMonth }) {
  // All chat bubbles — each is { id, role: 'user'|'ai', text }
  const [messages, setMessages] = useState([])

  // What the user is currently typing in the input box
  const [input, setInput] = useState('')

  // True while waiting for Claude's answer
  const [loading, setLoading] = useState(false)

  // Reference to the invisible div at the bottom of the message list
  // Used to auto-scroll after each new message
  const bottomRef = useRef(null)

  // ── Auto-scroll to bottom whenever messages change ─────────────────
  // Every time a new bubble is added (user or AI), scroll down.
  // behavior: 'smooth' makes it animate instead of jump.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // ── Reset chat when month changes ─────────────────────────────────
  // If the user switches from March to April, the old conversation
  // is about March's data. Clear it so there's no confusion.
  useEffect(() => {
    setMessages([])
  }, [selectedMonth])

  // ── Send handler ───────────────────────────────────────────────────
  async function handleSend() {
    // Don't send if empty or already waiting for a response
    if (!input.trim() || loading) return

    const question = input.trim()

    // Clear the input immediately — feels responsive
    setInput('')

    // Add the user's message to the chat thread right away
    // Don't wait for the API — optimistic UI update
    setMessages((prev) => [
      ...prev,
      { id: Date.now(), role: 'user', text: question },
    ])

    setLoading(true)

    try {
      const { start_date, end_date } = getMonthRange(selectedMonth)

      // POST /api/qa — backend fetches transactions, calls Claude, returns answer
      const response = await api.post('/qa', {
        question,
        start_date,
        end_date,
      })

      // Add Claude's answer as an AI bubble
      setMessages((prev) => [
        ...prev,
        { id: Date.now() + 1, role: 'ai', text: response.data.answer },
      ])
    } catch (err) {
      // If the API call fails, show an error bubble instead of crashing
      const errorMessage =
        err.response?.data?.detail || 'Could not get an answer. Please try again.'
      setMessages((prev) => [
        ...prev,
        { id: Date.now() + 1, role: 'ai', text: errorMessage },
      ])
    } finally {
      setLoading(false)
    }
  }

  // ── Render ─────────────────────────────────────────────────────────
  return (
    <div
      className="bg-white rounded-[14px] flex flex-col overflow-hidden"
      style={{ border: '1px solid #e8ecf4', minHeight: 280, flex: 1 }}
    >
      {/* Header */}
      <div
        className="px-[18px] py-3.5 flex items-center justify-between flex-shrink-0"
        style={{ borderBottom: '1px solid #f0f3f9' }}
      >
        <span className="text-[13px] font-semibold" style={{ color: '#0f1c3f' }}>
          Ask your finances
        </span>
        <span className="text-[11px]" style={{ color: '#9ca3af' }}>
          Ask anything
        </span>
      </div>

      {/* Message area */}
      {/* flex-1 means it grows to fill available space */}
      {/* overflow-y-auto adds a scrollbar only when content overflows */}
      <div className="flex-1 overflow-y-auto p-3.5 flex flex-col gap-2">
        {/* Show suggested questions only when no messages yet */}
        {messages.length === 0 && !loading && (
          <SuggestedQuestions onSelect={setInput} />
        )}

        {/* Render all chat bubbles */}
        {messages.map((m) => (
          <ChatBubble key={m.id} message={m} />
        ))}

        {/* Typing indicator — shown while loading */}
        {loading && <TypingIndicator />}

        {/* Invisible div at the bottom — scrolled into view after each message */}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div
        className="p-3 flex gap-2 flex-shrink-0"
        style={{ borderTop: '1px solid #f0f3f9' }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          // Enter key sends — Shift+Enter would be a newline (we just prevent default)
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSend()
            }
          }}
          placeholder="Ask anything about your finances..."
          className="flex-1 rounded-lg px-3 py-1.5 text-[11.5px] outline-none transition-all"
          style={{
            background: '#f4f6fb',
            border: '1px solid #e8ecf4',
            color: '#374151',
          }}
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className="text-[11px] font-semibold text-white px-3 py-1.5 rounded-lg transition-colors disabled:opacity-40"
          style={{ background: '#2563eb' }}
        >
          Ask
        </button>
      </div>
    </div>
  )
}