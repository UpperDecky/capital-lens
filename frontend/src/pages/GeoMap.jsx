/**
 * GeoMap -- World Intelligence Map
 * Layers: conflict pins, aircraft, maritime, fires, entities, landmarks, infrastructure
 * D3 Natural Earth choropleth + zoom/pan + tabbed live ticker
 */
import { useEffect, useRef, useState, useCallback } from 'react'
import * as d3 from 'd3'
import * as topojson from 'topojson-client'
import { timeAgo } from '../lib/format'

const BASE = ''

// -- Choropleth color scales
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

// -- Entity sector colors (squares on map)
const SECTOR_COLORS = {
  Technology:      '#2980b9',
  Finance:         '#27ae60',
  Energy:          '#e67e22',
  Defense:         '#e74c3c',
  Healthcare:      '#16a085',
  Media:           '#8e44ad',
  Commodities:     '#d35400',
  'Real Estate':   '#2c3e50',
  Retail:          '#c0392b',
  Industrials:     '#7f8c8d',
  individual:      '#9b59b6',
}

// -- Landmark type colors (diamonds on map)
const LANDMARK_COLORS = {
  chokepoint:  '#1a5276',
  military:    '#922b21',
  financial:   '#145a32',
  diplomatic:  '#4a235a',
  hotspot:     '#7b241c',
  exchange:    '#1e8449',
}

// -- Capital city coordinates [lon, lat] for entity/infra placement
const CAPITAL_COORDS = {
  US: [-77.04,  38.9 ], GB: [ -0.13,  51.50], FR: [  2.35,  48.85],
  DE: [ 13.40,  52.52], CN: [116.40,  39.91], RU: [ 37.62,  55.75],
  JP: [139.69,  35.69], IN: [ 77.22,  28.64], BR: [-47.93, -15.78],
  AU: [149.13, -35.28], CA: [-75.70,  45.42], KR: [126.98,  37.57],
  SA: [ 46.72,  24.69], IR: [ 51.42,  35.70], IL: [ 35.22,  31.78],
  UA: [ 30.52,  50.45], TR: [ 32.86,  39.93], PK: [ 73.06,  33.72],
  NG: [  7.49,   9.07], ZA: [ 28.19, -25.73], EG: [ 31.25,  30.06],
  ID: [106.85,  -6.21], MX: [-99.13,  19.43], AR: [-58.38, -34.61],
  VN: [105.85,  21.03], TH: [100.52,  13.75], MY: [101.69,   3.14],
  SG: [103.82,   1.35], PH: [120.98,  14.60], BD: [ 90.41,  23.72],
  ET: [ 38.75,   9.02], KE: [ 36.82,  -1.29], DZ: [  3.05,  36.75],
  MA: [ -6.85,  34.02], LY: [ 13.18,  32.90], SD: [ 32.53,  15.55],
  SO: [ 45.34,   2.05], AO: [ 13.23,  -8.84], CD: [ 15.32,  -4.32],
  TZ: [ 39.28,  -6.80], UZ: [ 69.30,  41.30], KZ: [ 71.45,  51.18],
  AF: [ 69.18,  34.52], IQ: [ 44.36,  33.34], SY: [ 36.29,  33.51],
  YE: [ 44.21,  15.35], LB: [ 35.50,  33.89], PS: [ 35.28,  31.90],
  MM: [ 96.09,  19.76], KP: [125.75,  39.02], TW: [121.55,  25.04],
  VE: [-66.87,  10.48], CO: [-74.08,   4.71], CL: [-70.67, -33.45],
  PE: [-77.03, -12.04], GR: [ 23.72,  37.98], PL: [ 21.01,  52.24],
  HU: [ 19.05,  47.49], RO: [ 26.10,  44.44], RS: [ 20.46,  44.82],
  BY: [ 27.57,  53.90], AZ: [ 49.87,  40.41], GE: [ 44.83,  41.69],
  AM: [ 44.50,  40.17], CU: [-82.37,  23.14], CZ: [ 14.47,  50.09],
  SE: [ 18.07,  59.33], NO: [ 10.75,  59.91], FI: [ 24.94,  60.17],
  DK: [ 12.57,  55.68], NL: [  4.90,  52.37], BE: [  4.35,  50.85],
  CH: [  7.47,  46.95], AT: [ 16.37,  48.21], ES: [ -3.70,  40.42],
  PT: [ -9.14,  38.72], IT: [ 12.50,  41.90], NZ: [174.78, -41.29],
  ZW: [ 31.05, -17.83], GH: [ -0.20,   5.55], LK: [ 79.86,   6.91],
  NP: [ 85.32,  27.72], MN: [106.91,  47.91], QA: [ 51.53,  25.29],
  AE: [ 54.37,  24.47], KW: [ 47.98,  29.37], OM: [ 58.59,  23.59],
  BH: [ 50.59,  26.22], JO: [ 35.93,  31.95], LU: [  6.13,  49.61],
}

// -- Strategic landmarks hardcoded on the map
const LANDMARKS = [
  { id: 'suez',        name: 'Suez Canal',              type: 'chokepoint',  lon:  32.35, lat:  30.60 },
  { id: 'hormuz',      name: 'Strait of Hormuz',         type: 'chokepoint',  lon:  56.50, lat:  26.60 },
  { id: 'malacca',     name: 'Strait of Malacca',        type: 'chokepoint',  lon: 103.50, lat:   2.50 },
  { id: 'bosphorus',   name: 'Bosphorus Strait',         type: 'chokepoint',  lon:  29.00, lat:  41.10 },
  { id: 'taiwan_str',  name: 'Taiwan Strait',            type: 'hotspot',     lon: 120.00, lat:  24.50 },
  { id: 'scs',         name: 'South China Sea',          type: 'hotspot',     lon: 114.00, lat:  15.00 },
  { id: 'bab_mandeb',  name: 'Bab el-Mandeb / Red Sea',  type: 'chokepoint',  lon:  43.50, lat:  13.00 },
  { id: 'panama',      name: 'Panama Canal',             type: 'chokepoint',  lon: -79.92, lat:   9.08 },
  { id: 'gibraltar',   name: 'Strait of Gibraltar',      type: 'chokepoint',  lon:  -5.35, lat:  35.98 },
  { id: 'cape_hope',   name: 'Cape of Good Hope',        type: 'chokepoint',  lon:  18.47, lat: -34.36 },
  { id: 'arctic',      name: 'Northern Sea Route',       type: 'chokepoint',  lon:  70.00, lat:  72.00 },
  { id: 'nato_hq',     name: 'NATO HQ (Brussels)',       type: 'military',    lon:   4.43, lat:  50.88 },
  { id: 'pentagon',    name: 'Pentagon',                 type: 'military',    lon: -77.06, lat:  38.87 },
  { id: 'diego_g',     name: 'Diego Garcia (US Base)',   type: 'military',    lon:  72.43, lat:  -7.32 },
  { id: 'guam',        name: 'Guam (US Base)',           type: 'military',    lon: 144.79, lat:  13.44 },
  { id: 'un_hq',       name: 'UN Headquarters',          type: 'diplomatic',  lon: -73.97, lat:  40.75 },
  { id: 'kremlin',     name: 'Kremlin',                  type: 'diplomatic',  lon:  37.62, lat:  55.75 },
  { id: 'zhongnanhai', name: 'Zhongnanhai (CCP HQ)',     type: 'diplomatic',  lon: 116.39, lat:  39.92 },
  { id: 'white_house', name: 'White House',              type: 'diplomatic',  lon: -77.04, lat:  38.90 },
  { id: 'davos',       name: 'Davos (WEF)',              type: 'diplomatic',  lon:   9.83, lat:  46.80 },
  { id: 'nyse',        name: 'NYSE / Wall Street',       type: 'exchange',    lon: -74.01, lat:  40.71 },
  { id: 'lse',         name: 'London Stock Exchange',    type: 'exchange',    lon:  -0.09, lat:  51.51 },
  { id: 'tse',         name: 'Tokyo Stock Exchange',     type: 'exchange',    lon: 139.77, lat:  35.68 },
  { id: 'sse',         name: 'Shanghai Stock Exchange',  type: 'exchange',    lon: 121.48, lat:  31.22 },
  { id: 'imf_wb',      name: 'IMF / World Bank (DC)',    type: 'financial',   lon: -77.04, lat:  38.90 },
]

// -- Deterministic jitter (same entity always gets same offset)
function hashOff(str, range) {
  let h = 0
  for (let i = 0; i < str.length; i++) {
    h = (Math.imul(31, h) + str.charCodeAt(i)) | 0
  }
  return (((h >>> 0) % 10000) / 10000 - 0.5) * range
}

function buildIsoMap(countries) {
  const map = {}
  for (const c of countries) if (c.iso_num) map[String(c.iso_num)] = c.iso2
  return map
}

function makeProjection(W, H) {
  return d3.geoNaturalEarth1().scale(W / 6.3).translate([W / 2, H / 2])
}

// ============================================================
// Sub-components
// ============================================================

function OverlayToggle({ label, color, active, count, onToggle }) {
  return (
    <button
      onClick={onToggle}
      className={`flex items-center gap-1.5 px-2.5 py-1.5 text-[10px] font-medium uppercase tracking-[0.06em] border transition-all ${
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
        <span className={`font-mono text-[9px] ${active ? 'text-white/70' : 'text-[#bbb]'}`}>
          {count > 9999 ? '9k+' : count}
        </span>
      )}
    </button>
  )
}

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

// -- Live ticker with tabs
function LiveTicker({ geoEvents, infraEvents, predMarkets, lastUpdated }) {
  const [tab, setTab] = useState('all')

  const allItems = [
    ...geoEvents.map(e  => ({ ...e,  _type: 'geo'   })),
    ...infraEvents.map(e => ({ ...e,  _type: 'infra' })),
  ].sort((a, b) => {
    const at = (a.occurred_at || a.started_at || '')
    const bt = (b.occurred_at || b.started_at || '')
    return bt.localeCompare(at)
  })

  const items =
    tab === 'all'     ? allItems     :
    tab === 'geo'     ? geoEvents    :
    tab === 'infra'   ? infraEvents  : []

  const TABS = [
    { key: 'all',     label: 'All',     count: allItems.length },
    { key: 'geo',     label: 'Geo',     count: geoEvents.length },
    { key: 'infra',   label: 'Infra',   count: infraEvents.length },
    { key: 'markets', label: 'Markets', count: predMarkets.length },
  ]

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-3 py-2 border-b border-[#e8e8e8] flex-shrink-0 bg-[#fafafa]">
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-[#e74c3c] animate-pulse" />
          <span className="text-[10px] font-bold uppercase tracking-widest text-[#111]">Live Intel</span>
        </div>
        {lastUpdated && (
          <span className="text-[9px] text-[#bbb]">{timeAgo(lastUpdated.toISOString())}</span>
        )}
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[#e8e8e8] flex-shrink-0">
        {TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex-1 py-1.5 text-[9px] font-medium uppercase tracking-[0.06em] transition-colors border-b-2 ${
              tab === t.key
                ? 'text-[#111] border-[#111]'
                : 'text-[#aaa] border-transparent hover:text-[#555]'
            }`}
          >
            {t.label}
            {t.count > 0 && (
              <span className={`ml-1 text-[8px] ${tab === t.key ? 'text-[#666]' : 'text-[#ccc]'}`}>
                {t.count > 999 ? '999+' : t.count}
              </span>
            )}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto">
        {tab === 'markets' ? (
          predMarkets.length === 0 ? (
            <div className="flex items-center justify-center h-24 text-xs text-[#bbb]">No prediction markets</div>
          ) : (
            predMarkets.map(m => <MarketTickerRow key={m.id} market={m} />)
          )
        ) : items.length === 0 ? (
          <div className="flex items-center justify-center h-24 text-xs text-[#bbb]">Waiting for events...</div>
        ) : (
          items.map(ev =>
            ev._type === 'infra'
              ? <InfraTickerRow key={ev.id} ev={ev} />
              : <TickerRow key={ev.id} ev={ev} />
          )
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

function InfraTickerRow({ ev }) {
  return (
    <div className="flex items-start gap-2 px-3 py-2.5 border-b border-[#f0f0f0] hover:bg-[#fffaf5] transition-colors">
      <span className="text-[8px] font-bold px-1.5 py-0.5 uppercase tracking-wider flex-shrink-0 mt-0.5 rounded-sm bg-[#fff3e0] text-[#e67e22]">
        INFRA
      </span>
      <div className="flex-1 min-w-0">
        <div className="text-[11px] text-[#111] leading-snug font-medium">
          {ev.outage_type}{ev.scope ? ` -- ${ev.scope}` : ''}
        </div>
        {ev.cause && (
          <div className="text-[10px] text-[#666] mt-0.5 truncate">{ev.cause}</div>
        )}
        <div className="flex items-center gap-1.5 mt-0.5">
          {ev.iso2 && (
            <span className="text-[9px] text-[#999] font-mono bg-[#f0f0f0] px-1 rounded">{ev.iso2}</span>
          )}
          <span className="text-[9px] text-[#bbb]">{timeAgo(ev.started_at)}</span>
        </div>
      </div>
    </div>
  )
}

function MarketTickerRow({ market }) {
  const yes = market.yes_price != null ? (market.yes_price * 100).toFixed(0) : null
  const no  = market.no_price  != null ? (market.no_price  * 100).toFixed(0) : null
  const vol = market.volume_usd ? `$${(market.volume_usd / 1e6).toFixed(1)}M` : null

  return (
    <div className="px-3 py-2.5 border-b border-[#f0f0f0] hover:bg-[#fafafa] transition-colors">
      <div className="text-[11px] text-[#111] leading-snug font-medium line-clamp-2">
        {market.question}
      </div>
      <div className="flex items-center gap-2 mt-1.5 flex-wrap">
        {yes && (
          <span className="text-[9px] font-mono bg-[#e8f8f0] text-[#27ae60] px-1.5 py-0.5 rounded">
            YES {yes}%
          </span>
        )}
        {no && (
          <span className="text-[9px] font-mono bg-[#fdf2f2] text-[#e74c3c] px-1.5 py-0.5 rounded">
            NO {no}%
          </span>
        )}
        {vol && <span className="text-[9px] text-[#bbb] ml-auto">{vol} vol</span>}
      </div>
      {market.entity_name && (
        <div className="text-[9px] text-[#999] mt-0.5 truncate">{market.entity_name}</div>
      )}
    </div>
  )
}

// ============================================================
// Main GeoMap component
// ============================================================
export default function GeoMap() {
  const svgRef  = useRef(null)
  const wrapRef = useRef(null)

  const [countries,       setCountries]       = useState([])
  const [isoMap,          setIsoMap]          = useState({})
  const [selected,        setSelected]        = useState(null)
  const [detail,          setDetail]          = useState(null)
  const [detailLoading,   setDetailLoading]   = useState(false)
  const [mode,            setMode]            = useState('conflict')
  const [tooltip,         setTooltip]         = useState(null)
  const [summary,         setSummary]         = useState({})
  const [stats,           setStats]           = useState({})
  const [liveEvents,      setLiveEvents]      = useState([])
  const [conflictPins,    setConflictPins]    = useState([])
  const [lastUpdated,     setLastUpdated]     = useState(null)

  // -- Existing overlays
  const [showAdsb,        setShowAdsb]        = useState(false)
  const [showFires,       setShowFires]       = useState(false)
  const [showMaritime,    setShowMaritime]    = useState(false)
  const [showConflicts,   setShowConflicts]   = useState(true)
  const [adsbData,        setAdsbData]        = useState([])
  const [firesData,       setFiresData]       = useState([])
  const [maritimeData,    setMaritimeData]    = useState([])
  const [overlayTooltip,  setOverlayTooltip]  = useState(null)

  // -- New overlays
  const [showLandmarks,   setShowLandmarks]   = useState(true)
  const [showEntities,    setShowEntities]    = useState(false)
  const [showInfra,       setShowInfra]       = useState(false)
  const [entitiesData,    setEntitiesData]    = useState([])
  const [infraMapData,    setInfraMapData]    = useState([])

  // -- Ticker data
  const [infraEvents,     setInfraEvents]     = useState([])
  const [predMarkets,     setPredMarkets]     = useState([])

  // -- Fetch helpers
  const fetchStats = useCallback(() => {
    fetch(`${BASE}/geo/stats`).then(r => r.json()).then(setStats).catch(() => {})
  }, [])

  const fetchLiveEvents = useCallback(() => {
    fetch(`${BASE}/geo/live?limit=120&hours=96`)
      .then(r => r.json())
      .then(data => { setLiveEvents(data); setLastUpdated(new Date()) })
      .catch(() => {})
  }, [])

  const fetchConflictPins = useCallback(() => {
    fetch(`${BASE}/geo/conflict-pins?limit=1000&days=14`)
      .then(r => r.json()).then(setConflictPins).catch(() => {})
  }, [])

  const fetchInfraEvents = useCallback(() => {
    fetch(`${BASE}/geo/infra?limit=200&hours=72`)
      .then(r => r.json())
      .then(data => { setInfraEvents(data); setInfraMapData(data) })
      .catch(() => {})
  }, [])

  // -- Initial load
  useEffect(() => {
    fetch(`${BASE}/geo/countries`).then(r => r.json()).then(data => {
      setCountries(data); setIsoMap(buildIsoMap(data))
    }).catch(() => {})
    fetch(`${BASE}/geo/summary`).then(r => r.json()).then(setSummary).catch(() => {})
    fetchStats()
    fetchLiveEvents()
    fetchConflictPins()
    fetchInfraEvents()
    // Entities (loaded once -- changes rarely)
    fetch(`${BASE}/geo/entities`).then(r => r.json()).then(setEntitiesData).catch(() => {})
    // Prediction markets (loaded once -- sorted by volume)
    fetch(`${BASE}/geo/predictions?limit=50`).then(r => r.json()).then(setPredMarkets).catch(() => {})
  }, []) // eslint-disable-line

  // -- Auto-refresh every 30s
  useEffect(() => {
    const id = setInterval(() => {
      fetchStats()
      fetchLiveEvents()
      fetchInfraEvents()
      if (showConflicts) fetchConflictPins()
      if (showAdsb)
        fetch(`${BASE}/geo/adsb?limit=2000&hours=12`).then(r => r.json()).then(setAdsbData).catch(() => {})
      if (showFires)
        fetch(`${BASE}/geo/fires?limit=2000&days=7`).then(r => r.json()).then(setFiresData).catch(() => {})
      if (showMaritime)
        fetch(`${BASE}/geo/maritime?limit=1000&hours=48`).then(r => r.json()).then(setMaritimeData).catch(() => {})
    }, 30000)
    return () => clearInterval(id)
  }, [showAdsb, showFires, showMaritime, showConflicts, fetchStats, fetchLiveEvents, fetchConflictPins, fetchInfraEvents]) // eslint-disable-line

  // -- On-demand overlay fetches
  useEffect(() => {
    if (showAdsb && adsbData.length === 0)
      fetch(`${BASE}/geo/adsb?limit=2000&hours=12`).then(r => r.json()).then(setAdsbData).catch(() => {})
  }, [showAdsb]) // eslint-disable-line

  useEffect(() => {
    if (showFires && firesData.length === 0)
      fetch(`${BASE}/geo/fires?limit=2000&days=7`).then(r => r.json()).then(setFiresData).catch(() => {})
  }, [showFires]) // eslint-disable-line

  useEffect(() => {
    if (showMaritime && maritimeData.length === 0)
      fetch(`${BASE}/geo/maritime?limit=1000&hours=48`).then(r => r.json()).then(setMaritimeData).catch(() => {})
  }, [showMaritime]) // eslint-disable-line

  // -- Country detail on selection
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

    const g = svg.append('g')

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

        // Ocean background
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

        // Country fills
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

        // ── Overlay: conflict pins
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
                .attr('attributeName', 'r').attr('values', '4;18')
                .attr('dur', '2.2s').attr('repeatCount', 'indefinite')
              ring.append('animate')
                .attr('attributeName', 'opacity').attr('values', '0.8;0')
                .attr('dur', '2.2s').attr('repeatCount', 'indefinite')
            })

          pinG.selectAll('.conflict-dot')
            .data(pinsWithPos)
            .enter().append('circle')
            .attr('class', 'conflict-dot')
            .attr('cx', d => d.px).attr('cy', d => d.py)
            .attr('r', 3.5)
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
              d3.select(this).attr('r', 3.5).attr('opacity', 0.85)
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
            .attr('r', d => !d.brightness ? 2 : Math.min(5.5, 1.5 + Math.sqrt(d.brightness / 60)))
            .attr('fill', d => FIRE_COLORS[d.confidence] || FIRE_COLORS.nominal)
            .attr('opacity', 0.72)
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
              d3.select(this).attr('opacity', 0.72)
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
            .attr('r', 2.5)
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
              d3.select(this).attr('r', 2.5).attr('opacity', 0.8)
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
            .attr('r', 2)
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
              d3.select(this).attr('r', 2).attr('opacity', 0.7)
              setOverlayTooltip(null)
            })
        }

        // ── Overlay: entity squares
        if (showEntities && entitiesData.length > 0) {
          const entG = g.append('g').attr('class', 'overlay-entities')
          const pinned = entitiesData
            .map(en => {
              const coords = CAPITAL_COORDS[en.country_iso2]
              if (!coords) return null
              const lon = coords[0] + hashOff(en.id + 'x', 2.2)
              const lat = coords[1] + hashOff(en.id + 'y', 2.2)
              const p = projection([lon, lat])
              return p ? { ...en, px: p[0], py: p[1] } : null
            })
            .filter(Boolean)

          entG.selectAll('.entity-sq')
            .data(pinned)
            .enter().append('rect')
            .attr('class', 'entity-sq')
            .attr('x', d => d.px - 4)
            .attr('y', d => d.py - 4)
            .attr('width', 8)
            .attr('height', 8)
            .attr('fill', d => SECTOR_COLORS[d.sector] || SECTOR_COLORS[d.type] || '#95a5a6')
            .attr('stroke', '#fff')
            .attr('stroke-width', 0.8)
            .attr('opacity', 0.88)
            .attr('cursor', 'pointer')
            .on('mouseenter', function(event, d) {
              d3.select(this).attr('opacity', 1).attr('stroke-width', 2)
              const [mx, my] = d3.pointer(event, wrapRef.current)
              setOverlayTooltip({ x: mx, y: my,
                text: `${d.name} -- ${d.sector || d.type} (${d.country_iso2})` })
            })
            .on('mousemove', function(event) {
              const [mx, my] = d3.pointer(event, wrapRef.current)
              setOverlayTooltip(t => t ? { ...t, x: mx, y: my } : null)
            })
            .on('mouseleave', function() {
              d3.select(this).attr('opacity', 0.88).attr('stroke-width', 0.8)
              setOverlayTooltip(null)
            })
        }

        // ── Overlay: infrastructure outages (orange triangles)
        if (showInfra && infraMapData.length > 0) {
          const infraG = g.append('g').attr('class', 'overlay-infra')
          const infraPinned = infraMapData
            .filter(d => d.iso2 && CAPITAL_COORDS[d.iso2])
            .map(d => {
              const [clon, clat] = CAPITAL_COORDS[d.iso2]
              const lon = clon + hashOff(d.id + 'ix', 1.8)
              const lat = clat + hashOff(d.id + 'iy', 1.8)
              const p = projection([lon, lat])
              return p ? { ...d, px: p[0], py: p[1] } : null
            })
            .filter(Boolean)

          infraG.selectAll('.infra-tri')
            .data(infraPinned)
            .enter().append('polygon')
            .attr('class', 'infra-tri')
            .attr('points', d => {
              const sz = 5
              return `${d.px},${d.py - sz} ${d.px + sz},${d.py + sz} ${d.px - sz},${d.py + sz}`
            })
            .attr('fill', '#e67e22')
            .attr('stroke', '#fff')
            .attr('stroke-width', 0.8)
            .attr('opacity', 0.88)
            .attr('cursor', 'pointer')
            .on('mouseenter', function(event, d) {
              d3.select(this).attr('opacity', 1)
              const [mx, my] = d3.pointer(event, wrapRef.current)
              setOverlayTooltip({ x: mx, y: my,
                text: `[INFRA] ${d.outage_type}${d.scope ? ' -- ' + d.scope : ''}${d.cause ? ' -- ' + d.cause : ''} (${d.iso2})` })
            })
            .on('mousemove', function(event) {
              const [mx, my] = d3.pointer(event, wrapRef.current)
              setOverlayTooltip(t => t ? { ...t, x: mx, y: my } : null)
            })
            .on('mouseleave', function() {
              d3.select(this).attr('opacity', 0.88)
              setOverlayTooltip(null)
            })
        }

        // ── Overlay: landmarks (diamond markers, always on top)
        if (showLandmarks) {
          const lmG = g.append('g').attr('class', 'overlay-landmarks')
          LANDMARKS.forEach(lm => {
            const p = projection([lm.lon, lm.lat])
            if (!p) return
            const [px, py] = p
            const sz = 6
            const pts = `${px},${py - sz} ${px + sz},${py} ${px},${py + sz} ${px - sz},${py}`
            lmG.append('polygon')
              .attr('points', pts)
              .attr('fill', LANDMARK_COLORS[lm.type] || '#111')
              .attr('stroke', '#fff')
              .attr('stroke-width', 1)
              .attr('opacity', 0.9)
              .attr('cursor', 'pointer')
              .on('mouseenter', function(event) {
                d3.select(this).attr('opacity', 1).attr('stroke-width', 2)
                const [mx, my] = d3.pointer(event, wrapRef.current)
                setOverlayTooltip({ x: mx, y: my,
                  text: `${lm.name} [${lm.type.toUpperCase()}]` })
              })
              .on('mousemove', function(event) {
                const [mx, my] = d3.pointer(event, wrapRef.current)
                setOverlayTooltip(t => t ? { ...t, x: mx, y: my } : null)
              })
              .on('mouseleave', function() {
                d3.select(this).attr('opacity', 0.9).attr('stroke-width', 1)
                setOverlayTooltip(null)
              })
          })
        }
      })
      .catch(err => console.error('[GeoMap]', err))
  }, [ // eslint-disable-line
    isoMap, countryMap, mode, selected,
    showAdsb, showFires, showMaritime, showConflicts,
    showLandmarks, showEntities, showInfra,
    adsbData, firesData, maritimeData, conflictPins,
    entitiesData, infraMapData,
  ])

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
        <div className="flex items-center gap-1 flex-wrap">
          <OverlayToggle label="Conflicts"  color="#e74c3c" active={showConflicts}
            count={conflictPins.length || undefined} onToggle={() => setShowConflicts(v => !v)} />
          <OverlayToggle label="Aircraft"   color="#2980b9" active={showAdsb}
            count={adsbData.length || undefined}     onToggle={() => setShowAdsb(v => !v)} />
          <OverlayToggle label="Vessels"    color="#16a085" active={showMaritime}
            count={maritimeData.length || undefined}  onToggle={() => setShowMaritime(v => !v)} />
          <OverlayToggle label="Fires"      color="#e67e22" active={showFires}
            count={firesData.length || undefined}     onToggle={() => setShowFires(v => !v)} />
          <OverlayToggle label="Entities"   color="#8e44ad" active={showEntities}
            count={entitiesData.length || undefined}  onToggle={() => setShowEntities(v => !v)} />
          <OverlayToggle label="Landmarks"  color="#1a5276" active={showLandmarks}
            count={LANDMARKS.length}                  onToggle={() => setShowLandmarks(v => !v)} />
          <OverlayToggle label="Infra"      color="#d35400" active={showInfra}
            count={infraMapData.filter(d => d.iso2 && CAPITAL_COORDS[d.iso2]).length || undefined}
            onToggle={() => setShowInfra(v => !v)} />
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
        <StatItem label="Active Conflicts" value={stats.active_conflicts}              color="#e74c3c" />
        <StatItem label="Events 24h"       value={stats.events_24h}                   color="#e67e22" />
        <StatItem label="Conflict Pins"    value={conflictPins.length || null}         color="#e74c3c" />
        <StatItem label="Aircraft"         value={stats.aircraft}                      color="#2980b9" />
        <StatItem label="Vessels"          value={stats.vessels}                       color="#16a085" />
        <StatItem label="Fires"            value={stats.fires}                         color="#e67e22" />
        <StatItem label="Entities"         value={entitiesData.length || null}         color="#8e44ad" />
        <StatItem label="Infra Alerts"     value={stats.infra_events || null}          color="#d35400" />
        <StatItem label="Markets"          value={stats.prediction_markets || null}    color="#145a32" />
        <div className="ml-auto flex items-center gap-2 px-3 py-1.5 flex-shrink-0">
          <span className="text-[9px] text-[#bbb]">
            {lastUpdated ? `Updated ${timeAgo(lastUpdated.toISOString())}` : 'Loading...'}
          </span>
          <span className="text-[9px] text-[#ddd]">|</span>
          <span className="text-[9px] text-[#bbb]">Auto 30s</span>
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
          <div className="absolute bottom-4 left-4 bg-white border border-[#e0e0e0] p-3 text-xs max-h-80 overflow-y-auto shadow-sm">
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

            {/* Overlay legends */}
            {(showConflicts || showFires || showAdsb || showMaritime || showEntities || showLandmarks || showInfra) && (
              <div className="mt-2 pt-2 border-t border-[#e8e8e8] space-y-1">
                {showConflicts && (
                  <>
                    <div className="text-[8px] uppercase tracking-wider text-[#999] mb-1">Conflicts</div>
                    {[['ACLED', '#e74c3c'], ['UCDP', '#9b59b6'], ['GDELT', '#3498db']].map(([k, c]) => (
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
                    {[['Airborne', '#2980b9'], ['On ground', '#e67e22']].map(([k, c]) => (
                      <div key={k} className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: c }} />
                        <span className="text-[10px] text-[#555]">{k}</span>
                      </div>
                    ))}
                  </>
                )}
                {showMaritime && (
                  <>
                    <div className="text-[8px] uppercase tracking-wider text-[#999] mt-1.5 mb-1">Vessels</div>
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-[#16a085] flex-shrink-0" />
                      <span className="text-[10px] text-[#555]">Vessel</span>
                    </div>
                  </>
                )}
                {showEntities && (
                  <>
                    <div className="text-[8px] uppercase tracking-wider text-[#999] mt-1.5 mb-1">Entities</div>
                    {Object.entries(SECTOR_COLORS).slice(0, 5).map(([k, c]) => (
                      <div key={k} className="flex items-center gap-2">
                        <span className="w-2 h-2 flex-shrink-0" style={{ background: c }} />
                        <span className="text-[10px] text-[#555]">{k}</span>
                      </div>
                    ))}
                  </>
                )}
                {showLandmarks && (
                  <>
                    <div className="text-[8px] uppercase tracking-wider text-[#999] mt-1.5 mb-1">Landmarks</div>
                    {Object.entries(LANDMARK_COLORS).map(([k, c]) => (
                      <div key={k} className="flex items-center gap-2">
                        <span className="w-2 h-2 rotate-45 flex-shrink-0" style={{ background: c }} />
                        <span className="text-[10px] text-[#555] capitalize">{k}</span>
                      </div>
                    ))}
                  </>
                )}
                {showInfra && (
                  <>
                    <div className="text-[8px] uppercase tracking-wider text-[#999] mt-1.5 mb-1">Infrastructure</div>
                    <div className="flex items-center gap-2">
                      <span className="text-[#d35400] text-[10px]">&#9650;</span>
                      <span className="text-[10px] text-[#555]">Outage / Alert</span>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right panel */}
        <div className="w-[320px] flex-shrink-0 border-l border-[#e0e0e0] flex flex-col overflow-hidden bg-white">
          {selected ? (
            detailLoading ? (
              <div className="flex-1 flex items-center justify-center text-xs text-[#999]">Loading...</div>
            ) : detail ? (
              <CountryPanel detail={detail} mode={mode} onClose={() => setSelected(null)} />
            ) : (
              <div className="flex-1 flex items-center justify-center text-xs text-[#999]">No data</div>
            )
          ) : (
            <LiveTicker
              geoEvents={liveEvents}
              infraEvents={infraEvents}
              predMarkets={predMarkets}
              lastUpdated={lastUpdated}
            />
          )}
        </div>
      </div>
    </div>
  )
}

// ============================================================
// Country detail panel
// ============================================================
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
        {/* Status row */}
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

        {/* Leadership */}
        {(detail.leader_name || detail.leader_title) && (
          <div className="border border-[#e8e8e8] p-3">
            <div className="text-[9px] uppercase tracking-widest text-[#999] mb-1.5">Leadership</div>
            <div className="text-xs text-[#111] font-semibold">{detail.leader_name}</div>
            {detail.leader_title && <div className="text-[11px] text-[#666] mt-0.5">{detail.leader_title}</div>}
          </div>
        )}

        {/* Alliances */}
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

        {/* Key issues */}
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

        {/* Infrastructure alerts for this country */}
        {detail.infra_events?.length > 0 && (
          <div>
            <div className="text-[9px] uppercase tracking-widest text-[#999] mb-2 flex items-center gap-2">
              Infra Alerts
              <span className="text-[8px] bg-[#fff3e0] text-[#e67e22] px-1.5 py-0.5 font-bold rounded">
                {detail.infra_events.length}
              </span>
            </div>
            <div className="space-y-1.5">
              {detail.infra_events.map(ev => (
                <div key={ev.id} className="border border-[#e8e8e8] p-2.5 bg-[#fffaf5]">
                  <div className="text-[11px] text-[#111] font-medium">{ev.outage_type}</div>
                  {ev.scope && <div className="text-[10px] text-[#666] mt-0.5">{ev.scope}</div>}
                  <div className="text-[9px] text-[#bbb] mt-0.5">{timeAgo(ev.started_at)}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Prediction markets for this country */}
        {detail.prediction_markets?.length > 0 && (
          <div>
            <div className="text-[9px] uppercase tracking-widest text-[#999] mb-2">Prediction Markets</div>
            <div className="space-y-2">
              {detail.prediction_markets.map(m => {
                const yes = m.yes_price != null ? (m.yes_price * 100).toFixed(0) : null
                const no  = m.no_price  != null ? (m.no_price  * 100).toFixed(0) : null
                return (
                  <div key={m.id} className="border border-[#e8e8e8] p-2.5">
                    <div className="text-[10px] text-[#111] leading-snug line-clamp-2">{m.question}</div>
                    <div className="flex items-center gap-2 mt-1">
                      {yes && <span className="text-[9px] bg-[#e8f8f0] text-[#27ae60] px-1.5 py-0.5 rounded font-mono">YES {yes}%</span>}
                      {no  && <span className="text-[9px] bg-[#fdf2f2] text-[#e74c3c] px-1.5 py-0.5 rounded font-mono">NO {no}%</span>}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Live news */}
        <div>
          <div className="text-[9px] uppercase tracking-widest text-[#999] mb-2 flex items-center gap-2">
            Live News
            <span className="w-1.5 h-1.5 bg-[#e74c3c] rounded-full animate-pulse" />
          </div>
          {detail.geo_events?.length > 0 ? (
            <div className="space-y-2">
              {detail.geo_events.slice(0, 10).map(ev => (
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

        {/* Capital Lens entity events */}
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
