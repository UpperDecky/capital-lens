/**
 * GeoMap -- World Intelligence Map
 * Live global tracking: conflict events, ADS-B aircraft, maritime vessels, satellite fires
 * D3 Natural Earth choropleth + overlay layers + zoom/pan + live event ticker
 */
import { useEffect, useRef, useState, useCallback } from 'react'
import * as d3 from 'd3'
import * as topojson from 'topojson-client'
import { timeAgo } from '../lib/format'

const BASE = ''

const CONFLICT_COLORS = {
  war:             '#c0392b',
  active_conflict: '#e67e22',
  tension:         '#f1c40f',
  stable:          '#27ae60',
  unknown:         '#bdc3c7',
}
const LEAN_COLORS = {
  far_left:      '#1a5276',
  left:          '#2980b9',
  centre_left:   '#7fb3d3',
  centre:        '#95a5a6',
  centre_right:  '#e59866',
  right:         '#e67e22',
  far_right:     '#922b21',
  authoritarian: '#6c3483',
  theocratic:    '#7d6608',
  unknown:       '#bdc3c7',
}
const CONFLICT_LABELS = {
  war: 'War', active_conflict: 'Active Conflict',
  tension: 'Tension', stable: 'Stable', unknown: 'Unknown',
}
const LEAN_LABELS = {
  far_left: 'Far Left', left: 'Left', centre_left: 'Centre Left',
  centre: 'Centre', centre_right: 'Centre Right', right: 'Right',
  far_right: 'Far Right', authoritarian: 'Authoritarian',
  theocratic: 'Theocratic', unknown: 'Unknown',
}
const FIRE_COLORS = { high: '#c0392b', nominal: '#e67e22', low: '#f1c40f' }

const SOURCE_COLORS = {
  ACLED:      '#e74c3c',
  UCDP:       '#9b59b6',
  GDELT:      '#3498db',
  Telegram:   '#16a085',
  Cloudflare: '#e67e22',
}
const SOURCE_BG = {
  ACLED:      '#fdf2f2',
  UCDP:       '#f7f0ff',
  GDELT:      '#f0f7ff',
  Telegram:   '#f0faf8',
  Cloudflare: '#fff8f0',
}

function buildIsoMap(countries) {
  const map = {}
  for (const c of countries) if (c.iso_num) map[String(c.iso_num)] = c.iso2
  return map
}

function makeProjection(W, H) {
  return d3.geoNaturalEarth1().scale(W / 6.3).translate([W / 2, H / 2])
}

// ── Overlay toggle button
function OverlayToggle({ label, color, active, count, onToggle }) {
  return (
    <button
      onClick={onToggle}
      className={`flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-medium uppercase tracking-[0.06em] border transition-all ${
        active
          ? 'text-white border-transparent'
          : 'border-[#e0e0e0] text-[#666] bg-white hover:border-[#999]'
      }`}
      style={active ? { background: color, borderColor: color } : {}}
    >
      <span
        className="w-2 h-2 rounded-full flex-shrink-0"
        style={{ background: active ? 'rgba(255,255,255,0.8)' : color }}
      />
      {label}
      {count != null && count > 0 && (
        <span className={`font-mono ${active ? 'text-white/70' : 'text-[#bbb]'}`}>
          {count > 9999 ? '9k+' : count}
        </span>
      )}
    </button>
  )
}

// ── Stats bar item
function StatItem({ label, value, color }) {
  return (
    <div className="flex items-center gap-1.5 px-3 py-1.5 border-r border-[#e8e8e8] last:border-0 flex-shrink-0">
      <span className="text-[9px] uppercase tracking-wider text-[#999] whitespace-nowrap">{label}</span>
      <span className="text-xs font-bold tabular-nums" style={{ color: color || '#111' }}>
        {value != null && value !== 0 ? value : '--'}
      </span>
    </div>
  )
}

// ── Live event ticker (right panel when no country selected)
function LiveTicker({ events, lastUpdated }) {
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#e8e8e8] flex-shrink-0 bg-[#fafafa]">
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-[#e74c3c] animate-pulse" />
          <span className="text-[10px] font-bold uppercase tracking-widest text-[#111]">Live Events</span>
        </div>
        {lastUpdated && (
          <span className="text-[9px] text-[#bbb]">{timeAgo(lastUpdated.toISOString())}</span>
        )}
      </div>
      <div className="flex-1 overflow-y-auto">
        {events.length === 0 ? (
          <div className="flex items-center justify-center h-32 text-xs text-[#bbb]">
            Waiting for events...
          </div>
        ) : (
          events.map(ev => <TickerRow key={ev.id} ev={ev} />)
        )}
      </div>
    </div>
  )
}

function TickerRow({ ev }) {
  const srcColor = SOURCE_COLORS[ev.source] || '#95a5a6'
  const srcBg    = SOURCE_BG[ev.source]    || '#f8f8f8'
  const tone     = ev.tone ?? 0
  const toneDot  = tone > 1 ? '#27ae60' : tone < -1 ? '#e74c3c' : '#bbb'

  return (
    <a
      href={ev.url || '#'}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-start gap-2 px-3 py-2.5 border-b border-[#f0f0f0] hover:bg-[#fafafa] transition-colors"
    >
      <span
        className="text-[8px] font-bold px-1.5 py-0.5 uppercase tracking-wider flex-shrink-0 mt-0.5 rounded-sm"
        style={{ color: srcColor, background: srcBg }}
      >
        {ev.source || '?'}
      </span>
      <div className="flex-1 min-w-0">
        <div className="text-[11px] text-[#111] leading-snug line-clamp-2 font-medium">
          {ev.headline}
        </div>
        <div className="flex items-center gap-1.5 mt-0.5">
          {ev.iso2 && (
            <span className="text-[9px] text-[#999] font-mono bg-[#f0f0f0] px-1 rounded">
              {ev.iso2}
            </span>
          )}
          <span className="text-[9px] text-[#bbb]">{timeAgo(ev.occurred_at)}</span>
          <span className="ml-auto w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: toneDot }} />
        </div>
      </div>
    </a>
  )
}

// ── Main GeoMap component
export default function GeoMap() {
  const svgRef  = useRef(null)
  const wrapRef = useRef(null)

  const [countries,      setCountries]      = useState([])
  const [isoMap,         setIsoMap]         = useState({})
  const [selected,       setSelected]       = useState(null)
  const [detail,         setDetail]         = useState(null)
  const [detailLoading,  setDetailLoading]  = useState(false)
  const [mode,           setMode]           = useState('conflict')
  const [tooltip,        setTooltip]        = useState(null)
  const [summary,        setSummary]        = useState({})
  const [stats,          setStats]          = useState({})
  const [liveEvents,     setLiveEvents]     = useState([])
  const [conflictPins,   setConflictPins]   = useState([])
  const [lastUpdated,    setLastUpdated]    = useState(null)

  const [showAdsb,       setShowAdsb]       = useState(false)
  const [showFires,      setShowFires]      = useState(false)
  const [showMaritime,   setShowMaritime]   = useState(false)
  const [showConflicts,  setShowConflicts]  = useState(true)
  const [adsbData,       setAdsbData]       = useState([])
  const [firesData,      setFiresData]      = useState([])
  const [maritimeData,   setMaritimeData]   = useState([])
  const [overlayTooltip, setOverlayTooltip] = useState(null)

  // ── Fetch helpers
  const fetchStats = useCallback(() => {
    fetch(`${BASE}/geo/stats`).then(r => r.json()).then(setStats).catch(() => {})
  }, [])

  const fetchLiveEvents = useCallback(() => {
    fetch(`${BASE}/geo/live?limit=80&hours=72`)
      .then(r => r.json())
      .then(data => { setLiveEvents(data); setLastUpdated(new Date()) })
      .catch(() => {})
  }, [])

  const fetchConflictPins = useCallback(() => {
    fetch(`${BASE}/geo/conflict-pins?limit=300&days=7`)
      .then(r => r.json()).then(setConflictPins).catch(() => {})
  }, [])

  // ── Initial load
  useEffect(() => {
    fetch(`${BASE}/geo/countries`).then(r => r.json()).then(data => {
      setCountries(data); setIsoMap(buildIsoMap(data))
    }).catch(() => {})
    fetch(`${BASE}/geo/summary`).then(r => r.json()).then(setSummary).catch(() => {})
    fetchStats()
    fetchLiveEvents()
    fetchConflictPins()
  }, []) // eslint-disable-line

  // ── Auto-refresh every 30s
  useEffect(() => {
    const id = setInterval(() => {
      fetchStats()
      fetchLiveEvents()
      if (showConflicts) fetchConflictPins()
      if (showAdsb)
        fetch(`${BASE}/geo/adsb?limit=1000&hours=12`).then(r => r.json()).then(setAdsbData).catch(() => {})
      if (showFires)
        fetch(`${BASE}/geo/fires?limit=1000&days=3`).then(r => r.json()).then(setFiresData).catch(() => {})
      if (showMaritime)
        fetch(`${BASE}/geo/maritime?limit=500&hours=24`).then(r => r.json()).then(setMaritimeData).catch(() => {})
    }, 30000)
    return () => clearInterval(id)
  }, [showAdsb, showFires, showMaritime, showConflicts, fetchStats, fetchLiveEvents, fetchConflictPins]) // eslint-disable-line

  // ── On-demand overlay fetches
  useEffect(() => {
    if (showAdsb && adsbData.length === 0)
      fetch(`${BASE}/geo/adsb?limit=1000&hours=12`).then(r => r.json()).then(setAdsbData).catch(() => {})
  }, [showAdsb]) // eslint-disable-line

  useEffect(() => {
    if (showFires && firesData.length === 0)
      fetch(`${BASE}/geo/fires?limit=1000&days=3`).then(r => r.json()).then(setFiresData).catch(() => {})
  }, [showFires]) // eslint-disable-line

  useEffect(() => {
    if (showMaritime && maritimeData.length === 0)
      fetch(`${BASE}/geo/maritime?limit=500&hours=24`).then(r => r.json()).then(setMaritimeData).catch(() => {})
  }, [showMaritime]) // eslint-disable-line

  // ── Country detail on selection
  useEffect(() => {
    if (!selected) { setDetail(null); return }
    setDetailLoading(true)
    fetch(`${BASE}/geo/countries/${selected}`)
      .then(r => r.json())
      .then(d => { setDetail(d); setDetailLoading(false) })
      .catch(() => { setDetail(null); setDetailLoading(false) })
  }, [selected])

  const countryMap = {}
  for (const c of countries) countryMap[c.iso2] = c

  // ── D3 map render
  useEffect(() => {
    if (!svgRef.current || !wrapRef.current) return
    const rect = wrapRef.current.getBoundingClientRect()
    const W = rect.width  > 0 ? rect.width  : 960
    const H = rect.height > 0 ? rect.height : 480

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()
    svg.attr('width', W).attr('height', H)

    const projection = makeProjection(W, H)
    const path = d3.geoPath().projection(projection)

    // Root group -- zoom transforms this
    const g = svg.append('g')

    // Zoom/pan
    const zoom = d3.zoom()
      .scaleExtent([1, 8])
      .on('zoom', event => g.attr('transform', event.transform))
    svg.call(zoom)
    svg.on('dblclick.zoom', () =>
      svg.transition().duration(400).call(zoom.transform, d3.zoomIdentity)
    )

    fetch('https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json')
      .then(r => r.json())
      .then(world => {
        const geojson = topojson.feature(world, world.objects.countries)

        // Ocean
        g.append('path')
          .datum({ type: 'Sphere' })
          .attr('fill', '#d6e8f5')
          .attr('d', path)

        // Graticule
        g.append('path')
          .datum(d3.geoGraticule()())
          .attr('fill', 'none')
          .attr('stroke', '#c8dcea')
          .attr('stroke-width', 0.35)
          .attr('d', path)

        // Countries
        g.selectAll('.country')
          .data(geojson.features)
          .enter().append('path')
          .attr('class', 'country')
          .attr('d', path)
          .attr('fill', feat => {
            const iso2 = isoMap[String(feat.id)]
            const c    = iso2 ? countryMap[iso2] : null
            if (!c) return '#cdd3d8'
            return mode === 'conflict'
              ? (CONFLICT_COLORS[c.conflict_status] || CONFLICT_COLORS.unknown)
              : (LEAN_COLORS[c.political_lean]      || LEAN_COLORS.unknown)
          })
          .attr('stroke', feat => isoMap[String(feat.id)] === selected ? '#111' : '#fff')
          .attr('stroke-width', feat => isoMap[String(feat.id)] === selected ? 2 : 0.5)
          .attr('cursor', 'pointer')
          .on('mouseenter', function(event, feat) {
            const iso2 = isoMap[String(feat.id)]
            const c    = iso2 ? countryMap[iso2] : null
            if (!c) return
            d3.select(this).attr('opacity', 0.72)
            const [mx, my] = d3.pointer(event, wrapRef.current)
            const statusLabel = mode === 'conflict'
              ? (CONFLICT_LABELS[c.conflict_status] || c.conflict_status)
              : (LEAN_LABELS[c.political_lean]      || c.political_lean)
            setTooltip({ x: mx, y: my, name: c.name, status: statusLabel, conflict: c.conflict_status })
          })
          .on('mousemove', function(event) {
            const [mx, my] = d3.pointer(event, wrapRef.current)
            setTooltip(t => t ? { ...t, x: mx, y: my } : null)
          })
          .on('mouseleave', function() {
            d3.select(this).attr('opacity', 1)
            setTooltip(null)
          })
          .on('click', function(event, feat) {
            event.stopPropagation()
            const iso2 = isoMap[String(feat.id)]
            if (iso2 && countryMap[iso2]) setSelected(prev => prev === iso2 ? null : iso2)
          })

        // Border mesh
        g.append('path')
          .datum(topojson.mesh(world, world.objects.countries, (a, b) => a !== b))
          .attr('fill', 'none').attr('stroke', '#fff').attr('stroke-width', 0.5).attr('d', path)

        // ── Overlay: conflict pins (ACLED/UCDP events with lat/lon)
        if (showConflicts && conflictPins.length > 0) {
          const SIX_HOURS = 6 * 3600 * 1000
          const now = Date.now()
          const pinG = g.append('g').attr('class', 'overlay-conflicts')

          const pinsWithPos = conflictPins
            .filter(d => d.latitude != null && d.longitude != null)
            .map(d => {
              const p = projection([d.longitude, d.latitude])
              return p ? { ...d, px: p[0], py: p[1] } : null
            })
            .filter(Boolean)

          // Pulse rings for events < 6h old
          pinsWithPos
            .filter(d => now - new Date(d.occurred_at).getTime() < SIX_HOURS)
            .forEach(d => {
              const ring = pinG.append('circle')
                .attr('cx', d.px).attr('cy', d.py)
                .attr('r', 5).attr('fill', 'none')
                .attr('stroke', SOURCE_COLORS[d.source] || '#e74c3c')
                .attr('stroke-width', 1.5)
                .attr('pointer-events', 'none')
              ring.append('animate')
                .attr('attributeName', 'r').attr('values', '4;16')
                .attr('dur', '2.2s').attr('repeatCount', 'indefinite')
              ring.append('animate')
                .attr('attributeName', 'opacity').attr('values', '0.8;0')
                .attr('dur', '2.2s').attr('repeatCount', 'indefinite')
            })

          // Filled dots
          pinG.selectAll('.conflict-dot')
            .data(pinsWithPos)
            .enter().append('circle')
            .attr('class', 'conflict-dot')
            .attr('cx', d => d.px).attr('cy', d => d.py)
            .attr('r', 4)
            .attr('fill', d => SOURCE_COLORS[d.source] || '#e74c3c')
            .attr('opacity', 0.85)
            .attr('cursor', 'pointer')
            .on('mouseenter', function(event, d) {
              d3.select(this).attr('r', 6).attr('opacity', 1)
              const [mx, my] = d3.pointer(event, wrapRef.current)
              setOverlayTooltip({ x: mx, y: my, text: `[${d.source}] ${d.headline}` })
            })
            .on('mousemove', function(event) {
              const [mx, my] = d3.pointer(event, wrapRef.current)
              setOverlayTooltip(t => t ? { ...t, x: mx, y: my } : null)
            })
            .on('mouseleave', function() {
              d3.select(this).attr('r', 4).attr('opacity', 0.85)
              setOverlayTooltip(null)
            })
        }

        // ── Overlay: satellite fires
        if (showFires && firesData.length > 0) {
          const fireG = g.append('g').attr('class', 'overlay-fires')
          fireG.selectAll('.fire-dot')
            .data(firesData.filter(d => d.latitude != null && d.longitude != null))
            .enter().append('circle')
            .attr('class', 'fire-dot')
            .attr('cx', d => { const p = projection([d.longitude, d.latitude]); return p ? p[0] : -999 })
            .attr('cy', d => { const p = projection([d.longitude, d.latitude]); return p ? p[1] : -999 })
            .attr('r', d => !d.brightness ? 2.5 : Math.min(6, 2 + Math.sqrt(d.brightness / 50)))
            .attr('fill', d => FIRE_COLORS[d.confidence] || FIRE_COLORS.nominal)
            .attr('opacity', 0.75)
            .attr('cursor', 'pointer')
            .on('mouseenter', function(event, d) {
              d3.select(this).attr('opacity', 1)
              const [mx, my] = d3.pointer(event, wrapRef.current)
              setOverlayTooltip({ x: mx, y: my,
                text: `Fire (${d.confidence || 'nominal'}) -- ${d.country_iso2 || 'Unknown'}${d.brightness ? ` -- ${d.brightness.toFixed(0)} MW` : ''}` })
            })
            .on('mousemove', function(event) {
              const [mx, my] = d3.pointer(event, wrapRef.current)
              setOverlayTooltip(t => t ? { ...t, x: mx, y: my } : null)
            })
            .on('mouseleave', function() {
              d3.select(this).attr('opacity', 0.75)
              setOverlayTooltip(null)
            })
        }

        // ── Overlay: maritime vessels
        if (showMaritime && maritimeData.length > 0) {
          const marG = g.append('g').attr('class', 'overlay-maritime')
          marG.selectAll('.ship-dot')
            .data(maritimeData.filter(d => d.latitude != null && d.longitude != null))
            .enter().append('circle')
            .attr('class', 'ship-dot')
            .attr('cx', d => { const p = projection([d.longitude, d.latitude]); return p ? p[0] : -999 })
            .attr('cy', d => { const p = projection([d.longitude, d.latitude]); return p ? p[1] : -999 })
            .attr('r', 3)
            .attr('fill', '#16a085')
            .attr('opacity', 0.8)
            .attr('cursor', 'pointer')
            .on('mouseenter', function(event, d) {
              d3.select(this).attr('r', 5).attr('opacity', 1)
              const [mx, my] = d3.pointer(event, wrapRef.current)
              setOverlayTooltip({ x: mx, y: my,
                text: `${d.ship_name || d.mmsi} -- ${d.flag_country || 'Unknown'}${d.speed_knots != null ? ` -- ${d.speed_knots.toFixed(1)} kn` : ''}` })
            })
            .on('mousemove', function(event) {
              const [mx, my] = d3.pointer(event, wrapRef.current)
              setOverlayTooltip(t => t ? { ...t, x: mx, y: my } : null)
            })
            .on('mouseleave', function() {
              d3.select(this).attr('r', 3).attr('opacity', 0.8)
              setOverlayTooltip(null)
            })
        }

        // ── Overlay: ADS-B aircraft
        if (showAdsb && adsbData.length > 0) {
          const adsbG = g.append('g').attr('class', 'overlay-adsb')
          adsbG.selectAll('.adsb-dot')
            .data(adsbData.filter(d => d.latitude != null && d.longitude != null))
            .enter().append('circle')
            .attr('class', 'adsb-dot')
            .attr('cx', d => { const p = projection([d.longitude, d.latitude]); return p ? p[0] : -999 })
            .attr('cy', d => { const p = projection([d.longitude, d.latitude]); return p ? p[1] : -999 })
            .attr('r', 2.5)
            .attr('fill', d => d.on_ground ? '#e67e22' : '#2980b9')
            .attr('opacity', 0.7)
            .attr('cursor', 'pointer')
            .on('mouseenter', function(event, d) {
              d3.select(this).attr('r', 5).attr('opacity', 1)
              const [mx, my] = d3.pointer(event, wrapRef.current)
              const alt = d.altitude_m ? `${Math.round(d.altitude_m * 3.28084).toLocaleString()} ft` : null
              setOverlayTooltip({ x: mx, y: my,
                text: `${d.callsign || d.icao24} (${d.origin_country || 'Unknown'})${alt ? ' -- ' + alt : ''} -- ${d.on_ground ? 'On ground' : 'Airborne'}` })
            })
            .on('mousemove', function(event) {
              const [mx, my] = d3.pointer(event, wrapRef.current)
              setOverlayTooltip(t => t ? { ...t, x: mx, y: my } : null)
            })
            .on('mouseleave', function() {
              d3.select(this).attr('r', 2.5).attr('opacity', 0.7)
              setOverlayTooltip(null)
            })
        }
      })
      .catch(err => console.error('[GeoMap]', err))
  }, [isoMap, countryMap, mode, selected, showAdsb, showFires, showMaritime, showConflicts, adsbData, firesData, maritimeData, conflictPins]) // eslint-disable-line

  const activeConflicts = stats.active_conflicts ?? '--'

  return (
    <div className="h-full flex flex-col pt-12 bg-white">
      {/* Header */}
      <div className="border-b border-[#e0e0e0] px-4 py-2 flex items-center justify-between flex-shrink-0 flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <div>
            <h1 className="text-sm font-bold uppercase tracking-widest text-[#111]">World Intelligence</h1>
            <p className="text-[10px] text-[#999] mt-0.5">Live global tracking -- click any country for details</p>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 bg-[#e74c3c]">
            <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
            <span className="text-[9px] font-bold text-white tracking-widest uppercase">Live</span>
          </div>
        </div>

        {/* Overlay toggles */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <OverlayToggle label="Conflicts" color="#e74c3c" active={showConflicts}
            count={conflictPins.length || undefined} onToggle={() => setShowConflicts(v => !v)} />
          <OverlayToggle label="Aircraft"  color="#2980b9" active={showAdsb}
            count={adsbData.length || undefined}     onToggle={() => setShowAdsb(v => !v)} />
          <OverlayToggle label="Vessels"   color="#16a085" active={showMaritime}
            count={maritimeData.length || undefined}  onToggle={() => setShowMaritime(v => !v)} />
          <OverlayToggle label="Fires"     color="#e67e22" active={showFires}
            count={firesData.length || undefined}     onToggle={() => setShowFires(v => !v)} />
        </div>

        {/* Mode toggle */}
        <div className="flex items-center border border-[#e0e0e0] text-xs font-medium uppercase tracking-[0.06em]">
          {[['conflict', 'Conflict'], ['lean', 'Political']].map(([key, label]) => (
            <button key={key} onClick={() => setMode(key)}
              className={`px-3 py-1.5 transition-colors ${mode === key ? 'bg-[#111] text-white' : 'text-[#999] hover:text-[#111]'}`}>
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Stats bar */}
      <div className="border-b border-[#e0e0e0] flex items-center flex-shrink-0 bg-[#fafafa] overflow-x-auto">
        <StatItem label="Active Conflicts" value={activeConflicts}              color="#e74c3c" />
        <StatItem label="Events 24h"       value={stats.events_24h}             color="#e67e22" />
        <StatItem label="Events 7d"        value={stats.events_7d}              color="#666" />
        <StatItem label="Conflict Pins"    value={conflictPins.length || null}  color="#e74c3c" />
        <StatItem label="Aircraft"         value={stats.aircraft}               color="#2980b9" />
        <StatItem label="Vessels"          value={stats.vessels}                color="#16a085" />
        <StatItem label="Fire Detections"  value={stats.fires}                  color="#e67e22" />
        <div className="ml-auto flex items-center gap-2 px-3 py-1.5 flex-shrink-0">
          <span className="text-[9px] text-[#bbb]">
            {lastUpdated ? `Updated ${timeAgo(lastUpdated.toISOString())}` : 'Loading...'}
          </span>
          <span className="text-[9px] text-[#ddd]">|</span>
          <span className="text-[9px] text-[#bbb]">Auto-refresh 30s</span>
        </div>
      </div>

      {/* Map + right panel */}
      <div className="flex flex-1 overflow-hidden">
        {/* Map area */}
        <div
          ref={wrapRef}
          className="flex-1 relative overflow-hidden bg-[#e8f2fa] cursor-default"
          onClick={() => setSelected(null)}
        >
          <svg ref={svgRef} className="w-full h-full" />

          {/* Country tooltip */}
          {tooltip && !overlayTooltip && (
            <div
              className="pointer-events-none absolute z-10 bg-white border border-[#e0e0e0] px-3 py-2 text-xs shadow-sm"
              style={{ left: tooltip.x + 14, top: tooltip.y - 10 }}
            >
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-sm flex-shrink-0"
                  style={{ background: CONFLICT_COLORS[tooltip.conflict] || CONFLICT_COLORS.unknown }} />
                <span className="font-semibold text-[#111]">{tooltip.name}</span>
              </div>
              <div className="text-[#666] mt-0.5 ml-4">{tooltip.status}</div>
            </div>
          )}

          {/* Overlay tooltip */}
          {overlayTooltip && (
            <div
              className="pointer-events-none absolute z-20 bg-[#111] text-white px-3 py-2 text-[11px] shadow-lg max-w-xs leading-snug"
              style={{ left: overlayTooltip.x + 14, top: overlayTooltip.y - 10 }}
            >
              {overlayTooltip.text}
            </div>
          )}

          {/* Zoom hint */}
          <div className="absolute top-3 right-3 text-[9px] text-[#888] bg-white/80 px-2 py-1 border border-[#e0e0e0]">
            Scroll to zoom &middot; Drag to pan &middot; Dbl-click to reset
          </div>

          {/* Legend */}
          <div className="absolute bottom-4 left-4 bg-white border border-[#e0e0e0] p-3 text-xs max-h-72 overflow-y-auto shadow-sm">
            <div className="font-semibold uppercase tracking-wider text-[#555] mb-2 text-[9px]">
              {mode === 'conflict' ? 'Conflict Status' : 'Political Lean'}
            </div>
            {mode === 'conflict'
              ? Object.entries(CONFLICT_LABELS).map(([k, label]) => (
                  <div key={k} className="flex items-center gap-2 mb-1">
                    <span className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ background: CONFLICT_COLORS[k] }} />
                    <span className="text-[10px] text-[#555]">{label}</span>
                    {summary[k] ? <span className="text-[10px] text-[#999] ml-auto pl-2">{summary[k]}</span> : null}
                  </div>
                ))
              : Object.entries(LEAN_LABELS).map(([k, label]) => (
                  <div key={k} className="flex items-center gap-2 mb-1">
                    <span className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ background: LEAN_COLORS[k] }} />
                    <span className="text-[10px] text-[#555]">{label}</span>
                  </div>
                ))
            }
            {(showConflicts || showFires || showAdsb || showMaritime) && (
              <div className="mt-2 pt-2 border-t border-[#e8e8e8] space-y-1">
                {showConflicts && (
                  <>
                    <div className="text-[8px] uppercase tracking-wider text-[#999] mb-1">Conflicts</div>
                    {[['ACLED', '#e74c3c'], ['UCDP', '#9b59b6']].map(([k, c]) => (
                      <div key={k} className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: c }} />
                        <span className="text-[10px] text-[#555]">{k}</span>
                      </div>
                    ))}
                  </>
                )}
                {showFires && (
                  <>
                    <div className="text-[8px] uppercase tracking-wider text-[#999] mt-1.5 mb-1">Fires</div>
                    {Object.entries(FIRE_COLORS).map(([k, c]) => (
                      <div key={k} className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: c }} />
                        <span className="text-[10px] text-[#555] capitalize">{k}</span>
                      </div>
                    ))}
                  </>
                )}
                {showAdsb && (
                  <>
                    <div className="text-[8px] uppercase tracking-wider text-[#999] mt-1.5 mb-1">Aircraft</div>
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-[#2980b9]" />
                      <span className="text-[10px] text-[#555]">Airborne</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-[#e67e22]" />
                      <span className="text-[10px] text-[#555]">On ground</span>
                    </div>
                  </>
                )}
                {showMaritime && (
                  <>
                    <div className="text-[8px] uppercase tracking-wider text-[#999] mt-1.5 mb-1">Vessels</div>
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-[#16a085]" />
                      <span className="text-[10px] text-[#555]">Vessel</span>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right panel: live ticker or country detail */}
        <div className="w-[300px] flex-shrink-0 border-l border-[#e0e0e0] flex flex-col overflow-hidden bg-white">
          {selected ? (
            detailLoading ? (
              <div className="flex-1 flex items-center justify-center text-xs text-[#999]">Loading...</div>
            ) : detail ? (
              <CountryPanel detail={detail} mode={mode} onClose={() => setSelected(null)} />
            ) : (
              <div className="flex-1 flex items-center justify-center text-xs text-[#999]">No data</div>
            )
          ) : (
            <LiveTicker events={liveEvents} lastUpdated={lastUpdated} />
          )}
        </div>
      </div>
    </div>
  )
}

// ── Country detail panel
function CountryPanel({ detail, mode, onClose }) {
  const conflictColor = CONFLICT_COLORS[detail.conflict_status] || CONFLICT_COLORS.unknown
  const leanColor     = LEAN_COLORS[detail.political_lean]      || LEAN_COLORS.unknown

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-start justify-between px-4 pt-4 pb-3 border-b border-[#e8e8e8] flex-shrink-0">
        <div>
          <div className="text-base font-bold text-[#111]">{detail.name}</div>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            {detail.continent && (
              <span className="text-[10px] border border-[#e0e0e0] px-2 py-0.5 text-[#666] uppercase tracking-wider">
                {detail.continent}
              </span>
            )}
            {detail.gov_type && (
              <span className="text-[10px] border border-[#e0e0e0] px-2 py-0.5 text-[#666]">
                {detail.gov_type}
              </span>
            )}
          </div>
        </div>
        <button onClick={onClose} className="text-[#999] hover:text-[#111] text-xl leading-none ml-2 mt-0.5">
          &times;
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
        <div className="flex gap-3">
          <div className="flex-1 border border-[#e8e8e8] p-3">
            <div className="text-[9px] uppercase tracking-widest text-[#999] mb-1.5">Conflict Status</div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-sm" style={{ background: conflictColor }} />
              <span className="text-xs font-semibold text-[#111]">
                {CONFLICT_LABELS[detail.conflict_status] || detail.conflict_status || 'Unknown'}
              </span>
            </div>
          </div>
          <div className="flex-1 border border-[#e8e8e8] p-3">
            <div className="text-[9px] uppercase tracking-widest text-[#999] mb-1.5">Political Lean</div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-sm" style={{ background: leanColor }} />
              <span className="text-xs font-semibold text-[#111]">
                {LEAN_LABELS[detail.political_lean] || detail.political_lean || 'Unknown'}
              </span>
            </div>
          </div>
        </div>

        {(detail.leader_name || detail.leader_title) && (
          <div className="border border-[#e8e8e8] p-3">
            <div className="text-[9px] uppercase tracking-widest text-[#999] mb-1.5">Leadership</div>
            <div className="text-xs text-[#111] font-semibold">{detail.leader_name}</div>
            {detail.leader_title && <div className="text-[11px] text-[#666] mt-0.5">{detail.leader_title}</div>}
          </div>
        )}

        {detail.alliances?.length > 0 && (
          <div>
            <div className="text-[9px] uppercase tracking-widest text-[#999] mb-1.5">Alliances</div>
            <div className="flex flex-wrap gap-1">
              {detail.alliances.map(a => (
                <span key={a} className="text-[10px] border border-[#e0e0e0] px-2 py-0.5 text-[#555]">{a}</span>
              ))}
            </div>
          </div>
        )}

        {detail.key_issues?.length > 0 && (
          <div>
            <div className="text-[9px] uppercase tracking-widest text-[#999] mb-1.5">Key Issues</div>
            <div className="flex flex-wrap gap-1">
              {detail.key_issues.map(i => (
                <span key={i} className="text-[10px] bg-[#f8f8f8] border border-[#e8e8e8] px-2 py-0.5 text-[#555]">{i}</span>
              ))}
            </div>
          </div>
        )}

        <div>
          <div className="text-[9px] uppercase tracking-widest text-[#999] mb-2 flex items-center gap-2">
            Live News
            <span className="w-1.5 h-1.5 bg-[#e74c3c] rounded-full animate-pulse" />
          </div>
          {detail.geo_events?.length > 0 ? (
            <div className="space-y-2">
              {detail.geo_events.slice(0, 8).map(ev => (
                <a key={ev.id} href={ev.url} target="_blank" rel="noopener noreferrer"
                  className="block border border-[#e8e8e8] p-2.5 hover:border-[#999] transition-colors">
                  <div className="text-[11px] text-[#111] leading-snug font-medium line-clamp-2">{ev.headline}</div>
                  <div className="flex items-center justify-between mt-1.5">
                    <span className="text-[10px] text-[#999]">{ev.source}</span>
                    <span className="text-[10px] text-[#bbb]">{timeAgo(ev.occurred_at)}</span>
                  </div>
                  {ev.tone != null && <ToneBar tone={ev.tone} />}
                </a>
              ))}
            </div>
          ) : (
            <div className="text-xs text-[#bbb] py-3 text-center border border-[#e8e8e8]">No recent news</div>
          )}
        </div>

        {detail.entity_events?.length > 0 && (
          <div>
            <div className="text-[9px] uppercase tracking-widest text-[#999] mb-2">Capital Lens Events</div>
            <div className="space-y-2">
              {detail.entity_events.map((ev, i) => (
                <div key={i} className="border border-[#e8e8e8] p-2.5">
                  <div className="text-[10px] font-semibold text-[#444] uppercase tracking-wider mb-1">{ev.entity_name}</div>
                  <div className="text-[11px] text-[#111] leading-snug">{ev.headline}</div>
                  {ev.plain_english && (
                    <div className="mt-1.5 pl-2 border-l-2 border-[#3498db] text-[10px] text-[#555]">{ev.plain_english}</div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function ToneBar({ tone }) {
  const clamped = Math.max(-10, Math.min(10, tone))
  const pct     = ((clamped + 10) / 20) * 100
  const color   = clamped > 1 ? '#27ae60' : clamped < -1 ? '#e74c3c' : '#95a5a6'
  return (
    <div className="flex items-center gap-1.5 mt-1">
      <div className="flex-1 h-1 bg-[#f0f0f0] rounded-full overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-[9px] text-[#bbb] tabular-nums w-8 text-right">
        {clamped > 0 ? '+' : ''}{clamped.toFixed(1)}
      </span>
    </div>
  )
}
