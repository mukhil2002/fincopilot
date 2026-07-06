// Sidebar.jsx
// The permanent left navigation panel.
// Deep navy background. Logo at top. Nav links in middle. User at bottom.
// 220px wide, never scrolls, always visible.

import { Link, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { supabase } from '../../lib/supabase'

// ─── Icon components ───────────────────────────────────────────────────────
// Simple SVG icons. Inline so you have zero external icon dependencies.
// Each returns a sized SVG — width/height controlled by className on parent.

function GridIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className="w-4 h-4">
      <rect x="1" y="1" width="6" height="6" rx="1.5" />
      <rect x="9" y="1" width="6" height="6" rx="1.5" />
      <rect x="1" y="9" width="6" height="6" rx="1.5" />
      <rect x="9" y="9" width="6" height="6" rx="1.5" />
    </svg>
  )
}

function ListIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4">
      <line x1="3" y1="4" x2="13" y2="4" />
      <line x1="3" y1="8" x2="13" y2="8" />
      <line x1="3" y1="12" x2="13" y2="12" />
    </svg>
  )
}

function TrendIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4">
      <polyline points="1,11 5,7 9,9 15,3" />
      <polyline points="11,3 15,3 15,7" />
    </svg>
  )
}

function DocIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4">
      <rect x="3" y="1" width="10" height="14" rx="1.5" />
      <line x1="6" y1="5" x2="10" y2="5" />
      <line x1="6" y1="8" x2="10" y2="8" />
      <line x1="6" y1="11" x2="8" y2="11" />
    </svg>
  )
}

function QuestionIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4">
      <circle cx="8" cy="8" r="6.5" />
      <path d="M6 6c0-1.1.9-2 2-2s2 .9 2 2c0 1-1 1.5-2 2v1" strokeLinecap="round" />
      <circle cx="8" cy="12" r="0.5" fill="currentColor" />
    </svg>
  )
}

function StarIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4">
      <path d="M8 1l1.8 3.6L14 5.3l-3 2.9.7 4.1L8 10.4l-3.7 1.9.7-4.1-3-2.9 4.2-.7z" />
    </svg>
  )
}

function GemIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <path d="M9 2L14 7H10V16H8V7H4L9 2Z" fill="white" />
    </svg>
  )
}

// ─── SidebarSection ─────────────────────────────────────────────────────────
// Renders a labelled group of nav items.
// label = the small uppercase text above the group ("MAIN", "AI TOOLS")
// children = the NavItem components inside this group

function SidebarSection({ label, children }) {
  return (
    <div className="mb-1">
      {/* 
        Section label — very small, very faint, uppercase.
        mt-3 gives breathing room between sections.
      */}
      <p
        className="text-[10px] font-semibold uppercase tracking-[0.08em] px-2 mb-1.5 mt-3"
        style={{ color: 'rgba(255,255,255,0.2)' }}
      >
        {label}
      </p>
      {/* space-y-0.5 = tiny gap between nav items */}
      <div className="space-y-0.5">{children}</div>
    </div>
  )
}

// ─── NavItem ────────────────────────────────────────────────────────────────
// A single navigation link in the sidebar.
// active = boolean, highlights this item
// badge = optional number pill (e.g. "247" transactions, "3" anomalies)
// badgeVariant = 'blue' or 'red' — controls the pill colour

function NavItem({ icon, label, to, active, badge, badgeVariant = 'blue' }) {
  return (
    <Link
      to={to}
      className={`
        flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-[13px] transition-all
        ${active ? 'font-medium text-white' : 'text-white/50 hover:text-white/80'}
      `}
      // Active items get a subtle blue tint background
      style={active ? { background: 'rgba(37,99,235,0.13)' } : undefined}
    >
      {/* Icon — opacity 100 when active, 70 when not */}
      <span className={`flex-shrink-0 ${active ? 'opacity-100' : 'opacity-70'}`}>
        {icon}
      </span>

      {/* Label — takes up remaining space */}
      <span className="flex-1">{label}</span>

      {/* Optional badge pill — only renders if badge prop is passed */}
      {badge && (
        <span
          className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${
            badgeVariant === 'red' ? 'text-red-300' : 'text-blue-300'
          }`}
          style={{
            background:
              badgeVariant === 'red'
                ? 'rgba(239,68,68,0.2)'
                : 'rgba(37,99,235,0.2)',
          }}
        >
          {badge}
        </span>
      )}
    </Link>
  )
}

// ─── Sidebar (main export) ───────────────────────────────────────────────────

export default function Sidebar() {
  // useLocation() tells us the current URL path.
  // We use it to highlight the active nav item.
  // e.g. if path is '/dashboard', Overview is active.
  const location = useLocation()

  // User state — we fetch the logged-in user's email from Supabase
  // and derive initials + a display name from it.
  const [userEmail, setUserEmail] = useState('')

  useEffect(() => {
    // getSession() returns the current auth session (or null if logged out)
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session?.user?.email) {
        setUserEmail(session.user.email)
      }
    })
  }, []) // empty array = run once on mount

  // Derive initials from email for the avatar circle
  // "jane.doe@example.com" → "JD"
  // If no name part, fall back to first two letters of email
  const initials = userEmail
    ? userEmail.split('@')[0].split(/[._-]/).map(p => p[0]?.toUpperCase()).join('').slice(0, 2)
    : '?'

  // Display name = everything before the @ sign
  const displayName = userEmail ? userEmail.split('@')[0] : 'Loading...'

  return (
    <aside
      className="w-[220px] flex flex-col flex-shrink-0"
      style={{ background: '#0f1c3f' }}
    >
      {/* ── Logo area ── */}
      <div className="px-5 py-[22px]" style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
        <div className="flex items-center gap-2.5">
          {/* Gradient icon box */}
          <div
            className="w-8 h-8 rounded-[10px] flex items-center justify-center flex-shrink-0"
            style={{ background: 'linear-gradient(135deg, #4f8ef7, #2563eb)' }}
          >
            <GemIcon />
          </div>
          <div>
            <div className="text-[15px] font-semibold text-white tracking-tight">
              FinCopilot
            </div>
            <div className="text-[10px] font-semibold tracking-[0.04em]" style={{ color: '#4f8ef7' }}>
              AI · BOOKKEEPING
            </div>
          </div>
        </div>
      </div>

      {/* ── Navigation ── */}
      {/* flex-1 makes nav take all available space between logo and user footer */}
      <nav className="flex-1 px-3 py-3.5 overflow-y-auto">
        <SidebarSection label="Main">
          <NavItem
            icon={<GridIcon />}
            label="Overview"
            to="/dashboard"
            active={location.pathname === '/dashboard'}
          />
          <NavItem
            icon={<ListIcon />}
            label="Transactions"
            to="/dashboard"
            active={location.pathname === '/transactions'}
          />
          <NavItem
            icon={<TrendIcon />}
            label="Forecast"
            to="/dashboard"
            active={location.pathname === '/forecast'}
          />
          <NavItem
            icon={<DocIcon />}
            label="Reports"
            to="/dashboard"
            active={location.pathname === '/reports'}
          />
        </SidebarSection>

        <SidebarSection label="AI Tools">
          <NavItem
            icon={<QuestionIcon />}
            label="Ask AI"
            to="/dashboard"
            active={location.pathname === '/ask'}
          />
          <NavItem
            icon={<StarIcon />}
            label="Anomalies"
            to="/dashboard"
            active={location.pathname === '/anomalies'}
            badgeVariant="red"
          />
        </SidebarSection>
      </nav>

      {/* ── User footer ── */}
      <div className="px-4 py-3.5" style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
        <div className="flex items-center gap-2.5">
          {/* Avatar circle with gradient — initials derived from email */}
          <div
            className="w-[30px] h-[30px] rounded-full flex items-center justify-center text-[11px] font-semibold text-white flex-shrink-0"
            style={{ background: 'linear-gradient(135deg, #4f8ef7, #7c3aed)' }}
          >
            {initials}
          </div>
          <div>
            <div
              className="text-[12px] font-medium truncate max-w-[130px]"
              style={{ color: 'rgba(255,255,255,0.8)' }}
            >
              {displayName}
            </div>
            <div className="text-[10px]" style={{ color: 'rgba(255,255,255,0.27)' }}>
              SME Owner
            </div>
          </div>
        </div>
      </div>
    </aside>
  )
}