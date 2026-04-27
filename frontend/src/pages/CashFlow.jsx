/**
 * CashFlow -- Global Capital Movement Map
 * Animated great-circle arcs on a dark world map showing crypto whale
 * transfers, OFAC sanctions, VC deals, and cross-border capital flows.
 */
import { useEffect, useRef, useState, useCallback } from 'react'
import * as d3 from 'd3'
import * as topojson from 'topojson-client'
import { formatAmount, timeAgo } from '../lib/format'

// ── Flow type config ──────────────────────────────────────────────────────────
const FLOW_META = {
  crypto_whale:  { color: '#f59e0b', label: 'Crypto Whale',   dot: '#fbbf24' },
  ofac_sanction: { color: '#ef4444', label: 'OFAC Sanction',  dot: '#fca5a5' },
  seizure:       { color: '#f97316', label: 'Asset Seizure',  dot: '#fdba74' },
  vc_deal:       { color: '#22c55e', label: 'VC / M&A',       dot: '#86efac' },
  fec_dark_money:{ color: '#8b5cf6', label: 'Dark Money',     dot: '#c4b5fd' },
  cross_border:  { color: '#60a5fa', label: 'Cross-Border',   dot: '#93c5fd' },
}
const ALL_TYPES  = Object.keys(FLOW_META)
const TYPE_ORDER = ['crypto_whale','ofac_sanction','seizure','vc_deal','fec_dark_money','cross_border']

function flowColor(type) {
  return (FLOW_META[type] || FLOW_META.cross_border).color
}
function flowLabel(type) {
  return (FLOW_META[type] || { label: type }).label
}

// ── Formatting helpers ────────────────────────────────────────────────────────
function fmtUSD(v) {
  if (!v || v === 0) return null
  if (v >= 1e12) return `$${(v / 1e12).toFixed(2)}T`
  if (v >= 1e9)  return `$${(v / 1e9).toFixed(1)}B`
  if (v >= 1e6)  return `$${(v / 1e6).toFixed(1)}M`
  if (v >= 1e3)  return `$${(v / 1e3).toFixed(0)}K`
  return `$${Math.round(v).toLocaleString()}`
}

function sumVolume(flows) {
  return flows.reduce((s, f) => s + (f.amount_usd || 0), 0)
}

// ── Projection helpers ────────────────────────────────────────────────────────
function makeProjection(W, H) {
  return d3.geoNaturalEarth1()
    .scale(W / 6.3)
    .translate([W / 2, H / 2])
}

// ── Arc animation injection ───────────────────────────────────────────────────
const ARC_STYLE = `
@keyframes cf-dash {
  from { stroke-dashoffset: var(--len); }
  to   { stroke-dashoffset: 0; }
}
@keyframes cf-dot {
  0%   { offset-distance: 0%;   opacity: 1; }
  80%  { offset-distance: 100%; opacity: 1; }
  100% { offset-distance: 100%; opacity: 0; }
}
@keyframes cf-fade {
  0%   { opacity: 0; }
  10%  { opacity: 1; }
  70%  { opacity: 1; }
  100% { opacity: 0; }
}
.cf-arc {
  animation: cf-fade 8s ease-in-out forwards;
}
.cf-arc-line {
  animation: cf-dash 3s ease-out forwards;
}
`

// ── Ticker item ───────────────────────────────────────────────────────────────
function TickerItem({ flow, onSelect }) {
  const color = flowColor(flow.flow_type)
  const amt   = fmtUSD(flow.amount_usd)
  return (
    <button
      onClick={() => onSelect(flow)}
      className="flex items-center gap-2 px-3 py-0 border-r border-white/5 flex-shrink-0 hover:bg-white/5 transition-colors h-full"
    >
      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: color }} />
      {amt && (
        <span className="font-mono text-[11px] font-bold" style={{ color }}>
          {amt}
        </span>
      )}
      <span className="text-[10px] text-white/60 uppercase tracking-wider flex-shrink-0">
        {flow.asset || flowLabel(flow.flow_type)}
      </span>
      {(flow.source_label || flow.dest_label) && (
        <span className="text-[10px] text-white/40 flex-shrink-0 max-w-[140px] truncate">
          {flow.source_label || '?'} &rarr; {flow.dest_label || '?'}
        </span>
      )}
      <span className="text-[9px] text-white/30 flex-shrink-0">
        {timeAgo(flow.occurred_at)}
      </span>
    </button>
  )
}

// ── Stat box ──────────────────────────────────────────────────────────────────
function StatBox({ label, value, sub }) {
  return (
    <div className="flex flex-col">
      <span className="text-[9px] uppercase tracking-[0.1em] text-white/40">{label}</span>
      <span className="text-sm font-bold font-mono text-white leading-tight">{value || '--'}</span>
      {sub && <span className="text-[9px] text-white/30">{sub}</span>}
    </div>
  )
}

// ── Detail panel ─────────────────────────────────────────────────────────────
function DetailPanel({ flow, stats, onClose }) {
  if (!flow && !stats) return null
  return (
    <div className="absolute right-0 top-0 bottom-0 w-72 bg-[#0d1117]/95 border-l border-white/10
                    backdrop-blur-sm flex flex-col overflow-hidden z-20">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
        <span className="text-[10px] font-semibold uppercase tracking-[0.1em] text-white/60">
          {flow ? 'Flow Detail' : 'Statistics'}
        </span>
        <button onClick={onClose} className="text-white/30 hover:text-white transition-colors text-xs">
          ✕
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {flow ? (
          /* Selected flow detail */
          <div className="p-4 space-y-4">
            <div className="flex items-start gap-2">
              <span
                className="w-2 h-2 rounded-full mt-1 flex-shrink-0"
                style={{ background: flowColor(flow.flow_type) }}
              />
              <p className="text-xs text-white/80 leading-relaxed">{flow.headline}</p>
            </div>
            {flow.amount_usd > 0 && (
              <div>
                <p className="text-[9px] text-white/30 uppercase tracking-wider mb-0.5">Amount</p>
                <p className="text-xl font-bold font-mono text-white">
                  {fmtUSD(flow.amount_usd)}
                </p>
              </div>
            )}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <p className="text-[9px] text-white/30 uppercase tracking-wider mb-0.5">Type</p>
                <p className="text-[11px] text-white/70" style={{ color: flowColor(flow.flow_type) }}>
                  {flowLabel(flow.flow_type)}
                </p>
              </div>
              {flow.asset && (
                <div>
                  <p className="text-[9px] text-white/30 uppercase tracking-wider mb-0.5">Asset</p>
                  <p className="text-[11px] text-white/70 font-mono">{flow.asset}</p>
                </div>
              )}
              <div>
                <p className="text-[9px] text-white/30 uppercase tracking-wider mb-0.5">From</p>
                <p className="text-[11px] text-white/70">
                  {flow.source_label || 'Unknown'} {flow.source_country && flow.source_country !== 'XX' ? `(${flow.source_country})` : ''}
                </p>
              </div>
              <div>
                <p className="text-[9px] text-white/30 uppercase tracking-wider mb-0.5">To</p>
                <p className="text-[11px] text-white/70">
                  {flow.dest_label || 'Unknown'} {flow.dest_country && flow.dest_country !== 'XX' ? `(${flow.dest_country})` : ''}
                </p>
              </div>
            </div>
            {flow.description && (
              <div>
                <p className="text-[9px] text-white/30 uppercase tracking-wider mb-1">Details</p>
                <p className="text-[11px] text-white/50 leading-relaxed line-clamp-6">
                  {flow.description}
                </p>
              </div>
            )}
            <div>
              <p className="text-[9px] text-white/30 uppercase tracking-wider mb-0.5">Source</p>
              <p className="text-[10px] text-white/40">{flow.source_name || 'Unknown'}</p>
            </div>
            <div>
              <p className="text-[9px] text-white/30 uppercase tracking-wider mb-0.5">Time</p>
              <p className="text-[10px] text-white/50">{timeAgo(flow.occurred_at)}</p>
            </div>
            {flow.source_url && (
              <a
                href={flow.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="block text-[10px] text-blue-400/70 hover:text-blue-300 underline underline-offset-2 truncate"
              >
                View source
              </a>
            )}
          </div>
        ) : stats ? (
          /* Stats overview */
          <div className="p-4 space-y-4">
            <div className="space-y-2">
              {TYPE_ORDER.map(type => {
                const row = stats.by_type?.find(r => r.flow_type === type)
                if (!row) return null
                return (
                  <div key={type} className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: flowColor(type) }} />
                    <span className="text-[10px] text-white/50 flex-1">{flowLabel(type)}</span>
                    <span className="text-[10px] font-mono text-white/70">{row.cnt}</span>
                    <span className="text-[10px] font-mono text-white/40 w-16 text-right">
                      {fmtUSD(row.volume_usd) || '--'}
                    </span>
                  </div>
                )
              })}
            </div>

            {stats.top_dest?.length > 0 && (
              <div>
                <p className="text-[9px] text-white/30 uppercase tracking-wider mb-2">
                  Top Destination Countries
                </p>
                {stats.top_dest.slice(0, 5).map(r => (
                  <div key={r.country} className="flex items-center gap-2 mb-1.5">
                    <span className="font-mono text-[10px] text-white/50 w-6">{r.country}</span>
                    <div className="flex-1 h-1 bg-white/10 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-white/30 rounded-full"
                        style={{ width: `${Math.min(100, (r.cnt / stats.total_flows) * 100 * 5)}%` }}
                      />
                    </div>
                    <span className="text-[9px] text-white/30 w-6 text-right">{r.cnt}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : null}
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────
export default function CashFlow() {
  const svgRef      = useRef(null)
  const wrapRef     = useRef(null)
  const arcGroupRef = useRef(null)

  const [flows,       setFlows]       = useState([])
  const [stats,       setStats]       = useState(null)
  const [loading,     setLoading]     = useState(true)
  const [activeTypes, setActiveTypes] = useState(new Set(ALL_TYPES))
  const [minAmount,   setMinAmount]   = useState(0)
  const [selected,    setSelected]    = useState(null)
  const [panelMode,   setPanelMode]   = useState(null) // 'flow' | 'stats' | null
  const [mapReady,    setMapReady]    = useState(false)
  const projRef     = useRef(null)
  const pathRef     = useRef(null)

  // ── Fetch data ──────────────────────────────────────────────────────────────
  const fetchStats = useCallback(() => {
    fetch('/cashflow/stats')
      .then(r => r.json())
      .then(setStats)
      .catch(() => {})
  }, [])

  const fetchFlows = useCallback(() => {
    fetch('/cashflow?limit=50&sort=recent')
      .then(r => r.json())
      .then(d => {
        setFlows(d.flows || [])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  useEffect(() => {
    fetchFlows()
    fetchStats()
    const id = setInterval(fetchFlows, 15000)
    return () => clearInterval(id)
  }, [fetchFlows])

  // ── Build world map ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (!svgRef.current || !wrapRef.current) return
    const rect = wrapRef.current.getBoundingClientRect()
    const W = rect.width  > 0 ? rect.width  : 1200
    const H = rect.height > 0 ? rect.height : 600

    const svg  = d3.select(svgRef.current)
    svg.selectAll('*').remove()
    svg.attr('width', W).attr('height', H)

    const projection = makeProjection(W, H)
    const geoPath    = d3.geoPath().projection(projection)
    projRef.current  = projection
    pathRef.current  = geoPath

    // ocean
    svg.append('rect')
      .attr('width', W).attr('height', H)
      .attr('fill', '#0d1117')

    fetch('https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json')
      .then(r => r.json())
      .then(world => {
        const geojson = topojson.feature(world, world.objects.countries)

        svg.append('path')
          .datum({ type: 'Sphere' })
          .attr('fill', '#111827')
          .attr('d', geoPath)

        svg.append('path')
          .datum(d3.geoGraticule()())
          .attr('fill', 'none')
          .attr('stroke', '#1f2937')
          .attr('stroke-width', 0.4)
          .attr('d', geoPath)

        svg.selectAll('.country')
          .data(geojson.features)
          .enter().append('path')
          .attr('class', 'country')
          .attr('d', geoPath)
          .attr('fill', '#1a2332')
          .attr('stroke', '#2a3447')
          .attr('stroke-width', 0.4)

        // arc group sits on top
        const g = svg.append('g').attr('class', 'arcs')
        arcGroupRef.current = g.node()

        setMapReady(true)
      })
      .catch(() => {})
  }, []) // eslint-disable-line

  // ── Draw / refresh arcs when flows or filters change ───────────────────────
  useEffect(() => {
    if (!mapReady || !arcGroupRef.current || !projRef.current) return

    const proj = projRef.current
    const g    = d3.select(arcGroupRef.current)
    g.selectAll('*').remove()

    const filtered = flows.filter(f => {
      if (!activeTypes.has(f.flow_type)) return false
      if (minAmount > 0 && (f.amount_usd || 0) < minAmount) return false
      const hasCoords = (
        f.source_lat != null && f.source_lon != null &&
        f.dest_lat   != null && f.dest_lon   != null &&
        !(f.source_lat === 0 && f.source_lon === 0) &&
        !(f.dest_lat   === 0 && f.dest_lon   === 0) &&
        !(f.source_lat === f.dest_lat && f.source_lon === f.dest_lon)
      )
      return hasCoords
    })

    filtered.forEach((flow, i) => {
      const src = proj([flow.source_lon, flow.source_lat])
      const dst = proj([flow.dest_lon,   flow.dest_lat])
      if (!src || !dst) return

      const color   = flowColor(flow.flow_type)
      const weight  = Math.max(1, Math.min(4, Math.log10((flow.amount_usd || 1e6) / 1e6) + 1))
      const delay   = (i % 12) * 0.4

      // Great-circle arc using geoPath
      const lineData = {
        type: 'LineString',
        coordinates: [[flow.source_lon, flow.source_lat], [flow.dest_lon, flow.dest_lat]],
      }
      const geoPathFn = d3.geoPath().projection(projRef.current)
      const dStr      = geoPathFn(lineData)
      if (!dStr) return

      // Animated arc group
      const arcG = g.append('g')
        .attr('class', 'cf-arc')
        .style('animation-delay', `${delay}s`)

      // Glow (wider, low opacity)
      arcG.append('path')
        .attr('d', dStr)
        .attr('fill', 'none')
        .attr('stroke', color)
        .attr('stroke-width', weight * 3)
        .attr('opacity', 0.12)

      // Main arc line (animated draw)
      const pathEl = arcG.append('path')
        .attr('class', 'cf-arc-line')
        .attr('d', dStr)
        .attr('fill', 'none')
        .attr('stroke', color)
        .attr('stroke-width', weight)
        .attr('opacity', 0.85)
        .style('animation-delay', `${delay}s`)

      // Set dash offset via JS (after DOM attach, so we can measure length)
      const node = pathEl.node()
      if (node) {
        const len = node.getTotalLength ? node.getTotalLength() : 400
        pathEl
          .attr('stroke-dasharray', len)
          .attr('stroke-dashoffset', len)
          .style('--len', len)
      }

      // Source dot
      arcG.append('circle')
        .attr('cx', src[0]).attr('cy', src[1])
        .attr('r', 3 + weight)
        .attr('fill', color)
        .attr('opacity', 0.9)

      // Dest dot (pulsing ring)
      arcG.append('circle')
        .attr('cx', dst[0]).attr('cy', dst[1])
        .attr('r', 2 + weight)
        .attr('fill', color)
        .attr('opacity', 0.9)

      arcG.append('circle')
        .attr('cx', dst[0]).attr('cy', dst[1])
        .attr('r', 5 + weight)
        .attr('fill', 'none')
        .attr('stroke', color)
        .attr('stroke-width', 1)
        .attr('opacity', 0.4)

      // Click to select
      arcG
        .attr('cursor', 'pointer')
        .on('click', () => {
          setSelected(flow)
          setPanelMode('flow')
        })
    })
  }, [flows, mapReady, activeTypes, minAmount])

  // ── Visible ticker flows (filtered) ────────────────────────────────────────
  const tickerFlows = flows.filter(f => {
    if (!activeTypes.has(f.flow_type)) return false
    if (minAmount > 0 && (f.amount_usd || 0) < minAmount) return false
    return true
  })

  const volume24h  = stats?.volume_24h  || sumVolume(flows)
  const totalFlows = stats?.total_flows || flows.length

  function toggleType(t) {
    setActiveTypes(prev => {
      const n = new Set(prev)
      if (n.has(t)) { if (n.size > 1) n.delete(t) } else n.add(t)
      return n
    })
  }

  const AMOUNT_PRESETS = [
    { label: 'All',   value: 0        },
    { label: '>$1M',  value: 1e6      },
    { label: '>$10M', value: 1e7      },
    { label: '>$100M',value: 1e8      },
    { label: '>$1B',  value: 1e9      },
  ]

  return (
    <div className="flex flex-col h-full pt-12 bg-[#0d1117] text-white overflow-hidden select-none">
      {/* Inject arc animation styles */}
      <style>{ARC_STYLE}</style>

      {/* ── Header bar ── */}
      <div className="flex-shrink-0 flex items-center gap-4 px-5 py-2.5 border-b border-white/10 bg-[#0d1117]/90 backdrop-blur-sm z-10">
        <div className="flex items-center gap-3 mr-2">
          <div className="flex flex-col">
            <span className="text-[9px] uppercase tracking-[0.12em] text-white/30">Cash Flow</span>
            <span className="text-xs font-bold text-white tracking-tight">Global Capital Monitor</span>
          </div>
          {volume24h > 0 && (
            <span className="text-sm font-bold font-mono text-white/70 border-l border-white/10 pl-3">
              {fmtUSD(volume24h)}
              <span className="text-[9px] text-white/30 font-normal ml-1">24h vol</span>
            </span>
          )}
          {totalFlows > 0 && (
            <span className="text-[10px] text-white/30 border-l border-white/10 pl-3">
              {totalFlows.toLocaleString()} flows
            </span>
          )}
        </div>

        {/* Flow type toggle pills */}
        <div className="flex items-center gap-1">
          {TYPE_ORDER.map(type => (
            <button
              key={type}
              onClick={() => toggleType(type)}
              className="flex items-center gap-1 px-2 py-0.5 text-[9px] font-medium uppercase tracking-wider border transition-all"
              style={activeTypes.has(type) ? {
                background: flowColor(type) + '22',
                borderColor: flowColor(type),
                color: flowColor(type),
              } : {
                borderColor: '#ffffff15',
                color: '#ffffff30',
              }}
            >
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: activeTypes.has(type) ? flowColor(type) : '#ffffff20' }} />
              {flowLabel(type)}
            </button>
          ))}
        </div>

        {/* Amount filter */}
        <div className="flex items-center gap-0.5 ml-auto border border-white/10 bg-white/5">
          {AMOUNT_PRESETS.map(p => (
            <button
              key={p.label}
              onClick={() => setMinAmount(p.value)}
              className="px-2 py-1 text-[9px] uppercase tracking-wider transition-colors"
              style={minAmount === p.value ? { background: '#ffffff15', color: '#ffffffcc' } : { color: '#ffffff40' }}
            >
              {p.label}
            </button>
          ))}
        </div>

        {/* Stats panel toggle */}
        <button
          onClick={() => setPanelMode(prev => prev === 'stats' ? null : 'stats')}
          className="px-2.5 py-1 text-[9px] uppercase tracking-wider border transition-colors"
          style={panelMode === 'stats' ? { borderColor: '#ffffff30', color: '#ffffff', background: '#ffffff10' } : { borderColor: '#ffffff15', color: '#ffffff40' }}
        >
          Stats
        </button>
      </div>

      {/* ── Map area ── */}
      <div ref={wrapRef} className="relative flex-1 overflow-hidden">
        <svg ref={svgRef} className="absolute inset-0" />

        {/* Loading overlay */}
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center">
            <p className="text-[11px] text-white/20 uppercase tracking-[0.15em] animate-pulse">
              Loading cash flow data...
            </p>
          </div>
        )}

        {/* No arc data notice */}
        {!loading && flows.filter(f =>
          activeTypes.has(f.flow_type) &&
          f.source_lat && f.source_lon && f.dest_lat && f.dest_lon &&
          !(f.source_lat === 0 && f.source_lon === 0) &&
          !(f.dest_lat   === 0 && f.dest_lon   === 0) &&
          !(f.source_lat === f.dest_lat && f.source_lon === f.dest_lon)
        ).length === 0 && mapReady && (
          <div className="absolute bottom-24 left-1/2 -translate-x-1/2">
            <p className="text-[10px] text-white/20 uppercase tracking-widest text-center">
              Arcs appear as geolocated flows arrive&nbsp;&mdash;&nbsp;OFAC and VC flows draw first
            </p>
          </div>
        )}

        {/* Legend bottom-left */}
        <div className="absolute bottom-4 left-4 flex flex-col gap-1.5">
          {TYPE_ORDER.filter(t => activeTypes.has(t)).map(type => (
            <div key={type} className="flex items-center gap-1.5">
              <span className="w-6 h-0.5 rounded-full" style={{ background: flowColor(type) }} />
              <span className="text-[9px] text-white/40 uppercase tracking-wider">{flowLabel(type)}</span>
            </div>
          ))}
        </div>

        {/* Live indicator */}
        <div className="absolute top-3 right-3 flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
          <span className="text-[9px] text-white/30 uppercase tracking-wider">Live</span>
        </div>

        {/* Detail panel */}
        {panelMode && (
          <DetailPanel
            flow={panelMode === 'flow' ? selected : null}
            stats={panelMode === 'stats' ? stats : null}
            onClose={() => { setPanelMode(null); setSelected(null) }}
          />
        )}
      </div>

      {/* ── Live ticker ── */}
      <div className="flex-shrink-0 h-10 border-t border-white/10 bg-[#060a0f] flex items-center overflow-hidden">
        {tickerFlows.length === 0 ? (
          <p className="w-full text-center text-[9px] text-white/20 uppercase tracking-widest">
            {loading ? 'Fetching flows...' : 'No flows match current filters'}
          </p>
        ) : (
          <div className="flex items-center h-full animate-none overflow-x-auto scrollbar-hide">
            <span className="flex-shrink-0 px-3 text-[9px] text-white/20 uppercase tracking-widest border-r border-white/10 h-full flex items-center">
              Live
            </span>
            {tickerFlows.map(f => (
              <TickerItem
                key={f.id}
                flow={f}
                onSelect={flow => { setSelected(flow); setPanelMode('flow') }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
