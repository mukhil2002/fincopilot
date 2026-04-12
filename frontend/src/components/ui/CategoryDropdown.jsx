// CategoryDropdown.jsx
// A floating dropdown for correcting a transaction's category
// Triggered when user clicks a CategoryBadge or the pencil icon
//
// Two responsibilities:
//   1. Show all 14 categories with their colours + checkmark on current
//   2. On selection → optimistic UI update + API call (stubbed for Day 14)
//
// "Optimistic UI" means: update the badge immediately on click,
// don't wait for the API to respond. Feels instant to the user.
// If the API fails, we revert. This is standard in modern web apps.

import { useEffect, useRef } from 'react'
import { BADGE_STYLES } from './CategoryBadge'

// Import the same 14 categories your backend uses
// This is the single source of truth — never hardcode the list again
const CATEGORIES = [
  'Revenue',
  'Operating Expenses',
  'Payroll',
  'Supplies',
  'Professional Fees',
  'Software & Subscriptions',
  'Utilities',
  'Travel & Transport',
  'Marketing & Advertising',
  'Bank Charges',
  'VAT Payment',
  'Transfers',
  'Personal / Drawings',
  'Other',
]

// ── Component ─────────────────────────────────────────────────────
// Props:
//   txn        = the full transaction object being corrected
//                we need txn.id for the API call + txn.category
//                to show the current selection with a checkmark
//   position   = { top, left } — where to render the dropdown
//                calculated by the parent so it appears near the badge
//   onSelect   = function(txnId, newCategory) — called after user picks
//                Parent updates its transactions state immediately
//   onClose    = function() — called to close the dropdown
//                triggered by: picking a category OR clicking outside
export function CategoryDropdown({ txn, position, onSelect, onClose }) {

  // ── Ref for click-outside detection ──────────────────────────
  // useRef gives us a direct reference to the dropdown DOM element
  // We need this to detect clicks OUTSIDE the dropdown → close it
  const dropdownRef = useRef(null)

  // ── Close on outside click ────────────────────────────────────
  // useEffect runs once when component mounts
  // Adds a mousedown listener to the whole document
  // If the click target is outside the dropdown → close it
  // Cleanup function removes the listener when component unmounts
  // Without cleanup: listener would pile up every time dropdown opens
  useEffect(() => {
    function handleClickOutside(event) {
      // dropdownRef.current = the actual <div> DOM node
      // contains() checks if the click was inside the dropdown
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        onClose()
      }
    }

    // 'mousedown' fires before 'click' — catches the press, not the release
    // This prevents the badge's onClick and this handler firing in the
    // wrong order and immediately reopening the dropdown
    document.addEventListener('mousedown', handleClickOutside)

    // Cleanup — React calls this when the dropdown is removed from the DOM
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [onClose])
  // ↑ onClose in dependency array — if parent passes a new function
  //   reference, we re-register the listener with the latest version

  // ── Handle category selection ─────────────────────────────────
  async function handleSelect(category) {
    // Don't do anything if user picks the same category
    if (category === txn.category) {
      onClose()
      return
    }

    // Step 1: Close the dropdown immediately — feels snappy
    onClose()

    // Step 2: Tell the parent to update the UI right now
    // This is the "optimistic" part — badge changes before API responds
    onSelect(txn.id, category)

    // Step 3: Save to backend
    // Stubbed for Day 14 — just a comment for now
    // On Day 14 replace this with:
    // await api.patch(`/transactions/${txn.id}/category`, { category })
    // The backend will also save to the corrections table automatically
    console.log(`Day 14: PATCH /api/transactions/${txn.id}/category →`, category)
  }

  // ── Render ────────────────────────────────────────────────────
  return (
    // fixed positioning — dropdown floats above everything else
    // position.top and position.left set by the parent
    // so it appears right below the badge that was clicked
    <div
      ref={dropdownRef}
      className="fixed z-50 bg-white rounded-xl py-1.5 overflow-y-auto"
      style={{
        top: position.top,
        left: position.left,
        width: 210,
        maxHeight: 260,
        border: '1px solid #e8ecf4',
        boxShadow: '0 8px 30px rgba(0,0,0,0.10)',
      }}
    >
      {/* Small header inside dropdown — helps user understand context */}
      <div
        className="px-3.5 py-2 text-[10px] font-semibold uppercase tracking-[0.06em]"
        style={{
          color: '#9ca3af',
          borderBottom: '1px solid #f0f3f9',
        }}
      >
        Change category
      </div>

      {/* Category list — one button per category */}
      {CATEGORIES.map(cat => {

        const isCurrentCategory = cat === txn.category

        // Look up this category's colour from BADGE_STYLES
        // Same colours as the badge — visual consistency
        const dotColour = BADGE_STYLES[cat]?.color ?? '#6b7280'

        return (
          <button
            key={cat}
            onClick={() => handleSelect(cat)}
            className="w-full text-left flex items-center justify-between px-3.5 py-1.5 text-[12px] transition-colors"
            style={{ color: '#374151' }}
            onMouseEnter={e => { e.currentTarget.style.background = '#f4f6fb' }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
          >
            {/* Left side: coloured dot + category name */}
            <span className="flex items-center gap-2">
              {/* Small dot in the category's brand colour */}
              {/* Gives a visual hint of the badge colour before selecting */}
              <span
                className="w-2 h-2 rounded-full flex-shrink-0"
                style={{ background: dotColour }}
              />
              {cat}
            </span>

            {/* Right side: checkmark if this is the current category */}
            {/* User immediately sees what the transaction is currently set to */}
            {isCurrentCategory && (
              <svg
                width="13" height="13"
                viewBox="0 0 13 13"
                fill="none"
              >
                <path
                  d="M2.5 6.5l3 3 5-5"
                  stroke="#2563eb"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            )}
          </button>
        )
      })}
    </div>
  )
}