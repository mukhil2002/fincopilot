// CategoryBadge.jsx
// A coloured pill badge that displays a transaction category
// Each category has a unique background + text + border colour
// Clicking it triggers the correction flow (wired on Day 14)

// ── Colour map ────────────────────────────────────────────────────
// Every category gets its own colour triplet: bg, text, border
// This is a plain JavaScript object — keys are category names,
// values are objects with three colour strings
const BADGE_STYLES = {
    'Revenue':                  { bg: '#ecfdf5', color: '#059669', border: '#a7f3d0' },
    'Payroll':                  { bg: '#eff4ff', color: '#2563eb', border: '#bfdbfe' },
    'Operating Expenses':       { bg: '#faf5ff', color: '#7c3aed', border: '#ddd6fe' },
    'Supplies':                 { bg: '#fffbeb', color: '#d97706', border: '#fde68a' },
    'Professional Fees':        { bg: '#fdf2f8', color: '#be185d', border: '#fbcfe8' },
    'Software & Subscriptions': { bg: '#eff6ff', color: '#0369a1', border: '#bae6fd' },
    'Utilities':                { bg: '#eef2ff', color: '#4338ca', border: '#c7d2fe' },
    'Travel & Transport':       { bg: '#fff7ed', color: '#c2410c', border: '#fed7aa' },
    'Marketing & Advertising':  { bg: '#fff1f2', color: '#be123c', border: '#fecdd3' },
    'Bank Charges':             { bg: '#f9fafb', color: '#6b7280', border: '#e5e7eb' },
    'VAT Payment':              { bg: '#fef2f2', color: '#dc2626', border: '#fecaca' },
    'Transfers':                { bg: '#ecfeff', color: '#0e7490', border: '#a5f3fc' },
    'Personal / Drawings':      { bg: '#f7fee7', color: '#4d7c0f', border: '#d9f99d' },
    'Other':                    { bg: '#f9fafb', color: '#6b7280', border: '#e5e7eb' },
  }
  
  // ── Component ─────────────────────────────────────────────────────
  // Props:
  //   category  = string  e.g. "Revenue", "Payroll"
  //   onClick   = function to call when user clicks the badge (optional)
  //               When provided: shows a pointer cursor + tooltip
  //               When absent: badge is just decorative
  export function CategoryBadge({ category, onClick }) {
  
    // Look up this category's colours in BADGE_STYLES
    // If the category doesn't exist in the map (e.g. a custom one),
    // fall back to the 'Other' style — never crash
    const s = BADGE_STYLES[category] ?? BADGE_STYLES['Other']
  
    return (
      <span
        onClick={onClick}
  
        // title = the little tooltip that appears on hover
        // Only show it if onClick is provided (i.e. it's clickable)
        title={onClick ? 'Click to correct category' : undefined}
  
        className="inline-flex items-center text-[10.5px] font-semibold px-2 py-[3px] rounded-full whitespace-nowrap transition-opacity"
  
        // cursor-pointer = hand cursor when hovering (if clickable)
        style={{
          background: s.bg,
          color: s.color,
          border: `1px solid ${s.border}`,
          cursor: onClick ? 'pointer' : 'default',
        }}
  
        // Slight fade on hover when clickable — gives tactile feedback
        onMouseEnter={e => { if (onClick) e.currentTarget.style.opacity = '0.75' }}
        onMouseLeave={e => { e.currentTarget.style.opacity = '1' }}
      >
        {category ?? 'Other'}
      </span>
    )
  }
  
  // Named export above — import like:
  // import { CategoryBadge } from '../ui/CategoryBadge'
  // Also export BADGE_STYLES so CategoryDropdown can reuse the colours
  export { BADGE_STYLES }