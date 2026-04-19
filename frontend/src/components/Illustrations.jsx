/**
 * Abstract SVG line drawings — 1–1.5px stroke, monochrome only.
 * Represent the movement of capital: pipes, nodes, arcs, ledger bars.
 */

/** Capital flowing through pipe channels — for empty feed state */
export function FlowEmpty({ size = 120 }) {
  return (
    <svg width={size} height={size * 0.7} viewBox="0 0 160 112" fill="none"
      xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      {/* Horizontal channels */}
      <line x1="8"  y1="28" x2="60" y2="28" stroke="#c0c0c0" strokeWidth="1"/>
      <line x1="8"  y1="56" x2="40" y2="56" stroke="#c0c0c0" strokeWidth="1"/>
      <line x1="8"  y1="84" x2="60" y2="84" stroke="#c0c0c0" strokeWidth="1"/>
      {/* Junction nodes */}
      <circle cx="60" cy="28" r="3" stroke="#999" strokeWidth="1" fill="none"/>
      <circle cx="40" cy="56" r="3" stroke="#999" strokeWidth="1" fill="none"/>
      <circle cx="60" cy="84" r="3" stroke="#999" strokeWidth="1" fill="none"/>
      {/* Vertical connectors */}
      <line x1="60" y1="31" x2="60" y2="53" stroke="#c0c0c0" strokeWidth="1"/>
      <line x1="60" y1="59" x2="60" y2="81" stroke="#c0c0c0" strokeWidth="1" strokeDasharray="3 2"/>
      {/* Transfer arcs */}
      <path d="M 60 28 Q 100 28 110 56" stroke="#888" strokeWidth="1.25" fill="none"/>
      <path d="M 60 84 Q 100 84 110 56" stroke="#888" strokeWidth="1.25" fill="none"/>
      {/* Destination node */}
      <circle cx="110" cy="56" r="5" stroke="#555" strokeWidth="1.25" fill="none"/>
      <circle cx="110" cy="56" r="2" fill="#999"/>
      {/* Output channel */}
      <line x1="115" y1="56" x2="152" y2="56" stroke="#c0c0c0" strokeWidth="1"/>
      {/* Flow tick marks */}
      <line x1="130" y1="52" x2="130" y2="60" stroke="#ccc" strokeWidth="1"/>
      <line x1="140" y1="52" x2="140" y2="60" stroke="#ccc" strokeWidth="1"/>
      {/* Ledger bars at bottom */}
      <line x1="8"  y1="104" x2="40"  y2="104" stroke="#ddd" strokeWidth="1"/>
      <line x1="8"  y1="108" x2="64"  y2="108" stroke="#ddd" strokeWidth="1"/>
      <line x1="8"  y1="112" x2="28"  y2="112" stroke="#ddd" strokeWidth="1"/>
    </svg>
  )
}

/** Oscilloscope scan — for loading state */
export function ScanWave({ size = 160 }) {
  return (
    <svg width={size} height={size * 0.3} viewBox="0 0 160 48" fill="none"
      xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <rect x="0" y="0" width="160" height="48" fill="none" stroke="#e0e0e0" strokeWidth="1"/>
      {/* Grid lines */}
      {[16, 32, 48, 64, 80, 96, 112, 128, 144].map(x => (
        <line key={x} x1={x} y1="0" x2={x} y2="48" stroke="#f0f0f0" strokeWidth="0.5"/>
      ))}
      {[12, 24, 36].map(y => (
        <line key={y} x1="0" y1={y} x2="160" y2={y} stroke="#f0f0f0" strokeWidth="0.5"/>
      ))}
      {/* Waveform */}
      <path
        d="M 0 24 L 20 24 L 22 16 L 24 32 L 26 16 L 28 32 L 30 24 L 60 24 L 62 10 L 68 38 L 74 10 L 76 24 L 100 24 L 102 20 L 104 28 L 106 20 L 108 24 L 160 24"
        stroke="#999" strokeWidth="1.25" fill="none"
      />
      {/* Cursor line */}
      <line x1="80" y1="2" x2="80" y2="46" stroke="#333" strokeWidth="1" strokeDasharray="2 2"/>
    </svg>
  )
}

/** Circuit board / transaction network — for search empty state */
export function NetworkEmpty({ size = 120 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 120 120" fill="none"
      xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      {/* Horizontal traces */}
      <line x1="0"   y1="40" x2="35"  y2="40" stroke="#d0d0d0" strokeWidth="1"/>
      <line x1="50"  y1="40" x2="85"  y2="40" stroke="#d0d0d0" strokeWidth="1"/>
      <line x1="100" y1="40" x2="120" y2="40" stroke="#d0d0d0" strokeWidth="1"/>
      <line x1="0"   y1="80" x2="20"  y2="80" stroke="#d0d0d0" strokeWidth="1"/>
      <line x1="35"  y1="80" x2="85"  y2="80" stroke="#d0d0d0" strokeWidth="1"/>
      <line x1="100" y1="80" x2="120" y2="80" stroke="#d0d0d0" strokeWidth="1"/>
      {/* Vertical traces */}
      <line x1="40"  y1="0"  x2="40"  y2="35"  stroke="#d0d0d0" strokeWidth="1"/>
      <line x1="40"  y1="50" x2="40"  y2="75"  stroke="#d0d0d0" strokeWidth="1"/>
      <line x1="40"  y1="90" x2="40"  y2="120" stroke="#d0d0d0" strokeWidth="1"/>
      <line x1="80"  y1="0"  x2="80"  y2="35"  stroke="#d0d0d0" strokeWidth="1"/>
      <line x1="80"  y1="50" x2="80"  y2="75"  stroke="#d0d0d0" strokeWidth="1"/>
      <line x1="80"  y1="90" x2="80"  y2="120" stroke="#d0d0d0" strokeWidth="1"/>
      {/* Intersection nodes */}
      {[[40,40],[80,40],[40,80],[80,80]].map(([x,y]) => (
        <rect key={`${x}${y}`} x={x-3} y={y-3} width="6" height="6"
          stroke="#888" strokeWidth="1" fill="#fff"/>
      ))}
      {/* Center node — larger */}
      <rect x="57" y="57" width="6" height="6" stroke="#333" strokeWidth="1.5" fill="#f5f5f5"/>
      {/* Diagonal traces */}
      <line x1="43" y1="43" x2="57" y2="57" stroke="#bbb" strokeWidth="1"/>
      <line x1="77" y1="43" x2="63" y2="57" stroke="#bbb" strokeWidth="1"/>
      <line x1="43" y1="77" x2="57" y2="63" stroke="#bbb" strokeWidth="1"/>
      <line x1="77" y1="77" x2="63" y2="63" stroke="#bbb" strokeWidth="1"/>
    </svg>
  )
}

/** Stacked ledger bars — for themes/no data state */
export function LedgerEmpty({ size = 120 }) {
  return (
    <svg width={size} height={size * 0.65} viewBox="0 0 160 104" fill="none"
      xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      {/* Ledger rows */}
      {[0,1,2,3,4,5].map(i => {
        const y    = i * 16 + 4
        const w    = [120, 88, 104, 64, 96, 48][i]
        const gray = ['#d0d0d0','#ccc','#d8d8d8','#c8c8c8','#d4d4d4','#bbb'][i]
        return (
          <g key={i}>
            <line x1="0" y1={y + 7} x2={w} y2={y + 7} stroke={gray} strokeWidth="6"/>
            <line x1="0" y1={y + 7} x2={w} y2={y + 7} stroke="#e8e8e8" strokeWidth="4"/>
            {/* Tick marks */}
            <line x1={w - 8} y1={y + 4} x2={w - 8} y2={y + 10} stroke="#bbb" strokeWidth="1"/>
          </g>
        )
      })}
      {/* Left margin rule */}
      <line x1="0" y1="0" x2="0" y2="104" stroke="#e0e0e0" strokeWidth="1"/>
    </svg>
  )
}

/** Money arc / transfer — decorative header accent */
export function TransferArc({ width = 200, height = 40 }) {
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}
      fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <path
        d={`M 0 ${height} Q ${width * 0.5} 0 ${width} ${height}`}
        stroke="#e0e0e0" strokeWidth="1" fill="none"
      />
      {/* Nodes at arc endpoints */}
      <circle cx="0"     cy={height} r="3" stroke="#ccc" strokeWidth="1" fill="none"/>
      <circle cx={width} cy={height} r="3" stroke="#ccc" strokeWidth="1" fill="none"/>
      {/* Midpoint tick */}
      <line x1={width * 0.5 - 1} y1="4" x2={width * 0.5 + 1} y2="12" stroke="#ccc" strokeWidth="1"/>
    </svg>
  )
}

/** Scan line loading bar */
export function ScanBar({ className = '' }) {
  return (
    <div className={`relative overflow-hidden bg-[#f0f0f0] h-px w-full ${className}`}>
      <div
        className="absolute inset-y-0 w-1/4 bg-gradient-to-r from-transparent via-[#999] to-transparent animate-scan"
      />
    </div>
  )
}

/** Skeleton block with scan animation */
export function SkeletonBlock({ className = '' }) {
  return (
    <div className={`scan-loading ${className}`} />
  )
}
