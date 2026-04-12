// ConfidenceBar.jsx
// Displays Claude's confidence score (0.0 → 1.0) as a small coloured bar
// Used in every transaction row to show how certain the AI was

// ── Colour logic ──────────────────────────────────────────────────
// Three thresholds — matches the design spec exactly:
//
//   0.90 – 1.00  →  green   (#059669)  Claude is confident, trust it
//   0.70 – 0.89  →  amber   (#f59e0b)  Probably right, worth checking
//   0.00 – 0.69  →  red     (#dc2626)  Claude was guessing, review it
//
// 1.00 exactly = human-confirmed correction → also green (full trust)

function getColour(confidence) {
    if (confidence >= 0.90) return '#059669'  // emerald green
    if (confidence >= 0.70) return '#f59e0b'  // amber
    return '#dc2626'                           // red
  }
  
  // ── Component ─────────────────────────────────────────────────────
  // Props:
  //   confidence = number between 0.0 and 1.0
  //                e.g. 0.96 = Claude is 96% confident
  //                     0.50 = default when Claude didn't return a score
  //                     1.00 = human-confirmed correction
  export function ConfidenceBar({ confidence }) {
  
    // Convert 0.0–1.0 to 0–100 for the CSS width percentage
    // Math.round: 0.9633 → 96  (cleaner than 96.33%)
    const pct = Math.round(confidence * 100)
  
    // Get the right colour for this score
    const colour = getColour(confidence)
  
    return (
      // Outer wrapper: bar + number sit side by side
      <div className="flex items-center gap-1.5">
  
        {/* The track — the grey background the bar sits on */}
        {/* w-11 = 44px wide, h-[3px] = 3px tall, very subtle */}
        <div
          className="w-11 h-[3px] rounded-full overflow-hidden"
          style={{ background: '#f0f3f9' }}   // light grey track
        >
          {/* The fill — width is the confidence percentage */}
          {/* e.g. confidence=0.96 → width: 96% → almost full bar */}
          <div
            className="h-full rounded-full"
            style={{
              width: `${pct}%`,
              background: colour,
            }}
          />
        </div>
  
        {/* The number next to the bar e.g. "0.96" */}
        {/* tabular-nums = all digits same width, so numbers don't jump */}
        {/* around when rows update — critical for tables */}
        <span
          className="text-[10px] tabular-nums"
          style={{ color: '#9ca3af' }}
        >
          {/* toFixed(2) = always show 2 decimal places */}
          {/* 0.9 → "0.90"  |  1 → "1.00"  |  0.5 → "0.50" */}
          {Number(confidence).toFixed(2)}
        </span>
  
      </div>
    )
  }