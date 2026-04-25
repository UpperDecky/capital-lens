/**
 * IntelCard — renders one intelligence-stream event.
 * Handles 5 types: geo_event | adsb | maritime | satellite | prediction
 */
import { timeAgo } from '../lib/format'

// ── Type metadata ─────────────────────────────────────────────────────────────
const TYPE_META = {
  geo_event:  { label: 'Geopolitical', accent: '#c0392b', icon: GeoIcon },
  adsb:       { label: 'Aircraft',     accent: '#2980b9', icon: AircraftIcon },
  maritime:   { label: 'Maritime',     accent: '#16a085', icon: ShipIcon },
  satellite:  { label: 'Satellite',    accent: '#e67e22', icon: FireIcon },
  prediction: { label: 'Prediction',   accent: '#8e44ad', icon: ChartIcon },
}

const SHIP_TYPE_LABELS = {
  '70': 'Cargo', '71': 'Cargo', '72': 'Cargo', '73': 'Cargo',
  '74': 'Cargo', '75': 'Cargo', '76': 'Cargo', '77': 'Cargo',
  '78': 'Cargo', '79': 'Cargo',
  '80': 'Tanker', '81': 'Tanker', '82': 'Tanker', '83': 'Tanker',
  '84': 'Tanker', '85': 'Tanker', '86': 'Tanker', '87': 'Tanker',
  '88': 'Tanker', '89': 'Tanker',
  '35': 'Military',
}

function shipTypeLabel(code) {
  if (!code) return 'Vessel'
  return SHIP_TYPE_LABELS[String(code)] || `Type ${code}`
}

function altFeet(m) {
  if (m == null) return null
  return Math.round(m * 3.28084).toLocaleString() + ' ft'
}

function knotsLabel(kn) {
  if (kn == null) return null
  return kn.toFixed(1) + ' kn'
}

function frpLabel(mw) {
  if (mw == null) return null
  return mw.toFixed(0) + ' MW'
}

function pctLabel(p) {
  if (p == null) return '?'
  return Math.round(p * 100) + '%'
}

// ── Icon components ───────────────────────────────────────────────────────────
function GeoIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
      <circle cx="6" cy="6" r="5" stroke="currentColor" strokeWidth="1.25"/>
      <path d="M6 1 Q8 6 6 11 Q4 6 6 1Z" stroke="currentColor" strokeWidth="1" fill="none"/>
      <line x1="1" y1="6" x2="11" y2="6" stroke="currentColor" strokeWidth="1"/>
    </svg>
  )
}
function AircraftIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
      <path d="M6 1L8 5H11L10 6.5H7.5L8 11H6L5 7.5H2.5L2 10H1L1.5 7H0.5L1.5 5H4L6 1Z"/>
    </svg>
  )
}
function ShipIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
      <path d="M2 7L1 10H11L10 7H2Z" stroke="currentColor" strokeWidth="1.25" fill="none"/>
      <path d="M4 7V4H8V7" stroke="currentColor" strokeWidth="1.25" fill="none"/>
      <line x1="6" y1="4" x2="6" y2="1" stroke="currentColor" strokeWidth="1.25"/>
    </svg>
  )
}
function FireIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
      <path d="M6 1C6 1 9 4 9 7C9 9.2 7.7 11 6 11C4.3 11 3 9.2 3 7C3 5.5 4 4 4 4C4 4 4.5 5.5 5.5 6C5.5 4.5 6 1 6 1Z"/>
    </svg>
  )
}
function ChartIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
      <rect x="1" y="7" width="2" height="4" fill="currentColor"/>
      <rect x="5" y="4" width="2" height="7" fill="currentColor"/>
      <rect x="9" y="2" width="2" height="9" fill="currentColor"/>
    </svg>
  )
}

// ── Tone bar (geo_event only) ─────────────────────────────────────────────────
function ToneBar({ tone }) {
  if (tone == null) return null
  const clamped = Math.max(-10, Math.min(10, tone))
  const pct = ((clamped + 10) / 20) * 100
  const color = clamped > 1 ? '#27ae60' : clamped < -1 ? '#e74c3c' : '#95a5a6'
  return (
    <div className="flex items-center gap-1.5 mt-1.5">
      <div className="flex-1 h-1 bg-[#f0f0f0] rounded-full overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-[9px] text-[#bbb] tabular-nums w-8 text-right">
        {clamped > 0 ? '+' : ''}{clamped.toFixed(1)}
      </span>
    </div>
  )
}

// ── Prediction price bar ──────────────────────────────────────────────────────
function PriceBar({ yes, no }) {
  const yesPct  = yes != null ? Math.round(yes * 100) : null
  const noPct   = no  != null ? Math.round(no  * 100) : null
  return (
    <div className="flex items-center gap-3 mt-2">
      <div className="flex-1">
        <div className="flex items-center justify-between mb-0.5">
          <span className="text-[9px] text-[#27ae60] font-semibold uppercase tracking-wider">Yes</span>
          <span className="text-[10px] font-mono font-bold text-[#27ae60]">{yesPct != null ? yesPct + '%' : '--'}</span>
        </div>
        <div className="h-1.5 bg-[#f0f0f0] rounded-full overflow-hidden">
          <div className="h-full bg-[#27ae60] rounded-full transition-all" style={{ width: `${yesPct ?? 0}%` }} />
        </div>
      </div>
      <div className="flex-1">
        <div className="flex items-center justify-between mb-0.5">
          <span className="text-[9px] text-[#e74c3c] font-semibold uppercase tracking-wider">No</span>
          <span className="text-[10px] font-mono font-bold text-[#e74c3c]">{noPct != null ? noPct + '%' : '--'}</span>
        </div>
        <div className="h-1.5 bg-[#f0f0f0] rounded-full overflow-hidden">
          <div className="h-full bg-[#e74c3c] rounded-full transition-all" style={{ width: `${noPct ?? 0}%` }} />
        </div>
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────
export default function IntelCard({ event }) {
  const meta = TYPE_META[event.intel_type] || TYPE_META.geo_event
  const Icon = meta.icon

  return (
    <div className="bg-white border border-[#e0e0e0] hover:border-[#bbb] transition-colors duration-150">
      {/* Left accent bar + header */}
      <div className="flex items-stretch">
        {/* Colour accent strip */}
        <div className="w-1 flex-shrink-0" style={{ background: meta.accent }} />

        <div className="flex-1 px-4 py-3">
          {/* Type badge + source + time */}
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span
                className="flex items-center gap-1 text-[9px] font-semibold uppercase tracking-widest px-1.5 py-0.5 border"
                style={{ borderColor: meta.accent, color: meta.accent }}
              >
                <Icon /> {meta.label}
              </span>
              {event.source && (
                <span className="text-[9px] text-[#999] uppercase tracking-wider">
                  {event.source}
                </span>
              )}
              {event.iso2 && (
                <span className="text-[9px] text-[#bbb] uppercase font-mono">
                  {event.iso2}
                </span>
              )}
            </div>
            <span className="text-[10px] text-[#bbb] flex-shrink-0">
              {timeAgo(event.occurred_at)}
            </span>
          </div>

          {/* Headline */}
          {event.intel_type === 'prediction' ? (
            <p className="text-xs text-[#111] leading-snug font-medium">
              {event.headline}
            </p>
          ) : event.url ? (
            <a
              href={event.url}
              target="_blank"
              rel="noopener noreferrer"
              className="block text-xs text-[#111] leading-snug font-medium hover:text-[#555] transition-colors"
            >
              {event.headline}
            </a>
          ) : (
            <p className="text-xs text-[#111] leading-snug font-medium">
              {event.headline}
            </p>
          )}

          {/* Type-specific detail row */}
          <DetailRow event={event} />
        </div>
      </div>
    </div>
  )
}

// ── Per-type detail rows ──────────────────────────────────────────────────────
function DetailRow({ event }) {
  const type = event.intel_type

  if (type === 'geo_event') {
    return (
      <div>
        <ToneBar tone={event.tone} />
        {event.themes?.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1.5">
            {event.themes.slice(0, 4).map(t => (
              <span key={t} className="text-[9px] border border-[#e8e8e8] px-1.5 py-0.5 text-[#888]">{t}</span>
            ))}
          </div>
        )}
      </div>
    )
  }

  if (type === 'adsb') {
    const alt   = altFeet(event.altitude_m)
    const speed = event.velocity_ms != null ? Math.round(event.velocity_ms * 1.944) + ' kn' : null
    return (
      <div className="flex flex-wrap gap-3 mt-2">
        {event.callsign && (
          <Stat label="Callsign" value={event.callsign} />
        )}
        {alt && <Stat label="Altitude" value={alt} />}
        {speed && <Stat label="Speed" value={speed} />}
        <Stat
          label="Status"
          value={event.on_ground ? 'On ground' : 'Airborne'}
          color={event.on_ground ? '#e67e22' : '#27ae60'}
        />
      </div>
    )
  }

  if (type === 'maritime') {
    return (
      <div className="flex flex-wrap gap-3 mt-2">
        {event.ship_type && (
          <Stat label="Type" value={shipTypeLabel(event.ship_type)} />
        )}
        {event.speed_knots != null && (
          <Stat label="Speed" value={knotsLabel(event.speed_knots)} />
        )}
        {event.destination && (
          <Stat label="Dest" value={event.destination.slice(0, 20)} />
        )}
        {event.lat != null && event.lon != null && (
          <Stat label="Position" value={`${event.lat.toFixed(2)}, ${event.lon.toFixed(2)}`} />
        )}
      </div>
    )
  }

  if (type === 'satellite') {
    return (
      <div className="flex flex-wrap gap-3 mt-2">
        <Stat label="Confidence" value={event.confidence || 'nominal'}
          color={event.confidence === 'high' ? '#e74c3c' : event.confidence === 'low' ? '#95a5a6' : '#e67e22'}
        />
        {event.brightness != null && (
          <Stat label="FRP" value={frpLabel(event.brightness)} />
        )}
        {event.lat != null && event.lon != null && (
          <Stat label="Location" value={`${event.lat.toFixed(2)}, ${event.lon.toFixed(2)}`} />
        )}
      </div>
    )
  }

  if (type === 'prediction') {
    return (
      <div>
        <PriceBar yes={event.yes_price} no={event.no_price} />
        {event.volume_usd != null && (
          <div className="mt-1.5 text-[10px] text-[#999]">
            Vol: <span className="font-mono text-[#666]">${Number(event.volume_usd).toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
          </div>
        )}
      </div>
    )
  }

  return null
}

function Stat({ label, value, color }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[9px] text-[#bbb] uppercase tracking-wider">{label}</span>
      <span className="text-[10px] font-mono text-[#444]" style={color ? { color } : {}}>
        {value}
      </span>
    </div>
  )
}
