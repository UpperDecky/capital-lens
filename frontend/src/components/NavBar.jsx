import { NavLink, useNavigate } from 'react-router-dom'
import { useEffect, useState, useRef, useCallback } from 'react'
import { api } from '../lib/api'
import { ScanBar } from './Illustrations'
import { useAlerts } from '../hooks/useAlerts'
import { useWatchlist } from '../hooks/useWatchlist'
import { timeAgo } from '../lib/format'

const links = [
  { to: '/',           label: 'Feed'       },
  { to: '/entities',   label: 'Entities'   },
  { to: '/watchlist',  label: 'Watchlist'  },
  { to: '/flowmap',    label: 'Flow Map'   },
  { to: '/world',      label: 'World'      },
  { to: '/cashflow',   label: 'Cash Flow'  },
  { to: '/themes',     label: 'Themes'     },
  { to: '/search',     label: 'Search'     },
]

// Color per alert intel_type
const ALERT_COLORS = {
  financial:  '#111111',
  geo_event:  '#c0392b',
  prediction: '#8e44ad',
  adsb:       '#2980b9',
  maritime:   '#16a085',
  satellite:  '#e67e22',
}

const ALERT_LABELS = {
  financial:  'Financial',
  geo_event:  'Geopolitical',
  prediction: 'Prediction',
  adsb:       'Aircraft',
  maritime:   'Maritime',
  satellite:  'Satellite',
}

function alertNavTarget(type) {
  if (type === 'financial') return '/'
  if (type === 'geo_event') return '/world'
  return '/'
}

function BellIcon({ unread }) {
  return (
    <div className="relative">
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="text-[#666]">
        <path
          d="M8 1.5C5.51 1.5 3.5 3.51 3.5 6v4l-1 1.5h11L12.5 10V6C12.5 3.51 10.49 1.5 8 1.5Z"
          stroke="currentColor" strokeWidth="1.25" fill="none"
        />
        <path d="M6.5 13.5a1.5 1.5 0 003 0" stroke="currentColor" strokeWidth="1.25" fill="none"/>
      </svg>
      {unread > 0 && (
        <span className="absolute -top-1 -right-1 min-w-[14px] h-[14px] bg-[#e74c3c] rounded-full flex items-center justify-center">
          <span className="text-white font-bold leading-none" style={{ fontSize: 8 }}>
            {unread > 9 ? '9+' : unread}
          </span>
        </span>
      )}
    </div>
  )
}

function AlertRow({ alert, onClick }) {
  const color = ALERT_COLORS[alert.intel_type] || '#999'
  const label = ALERT_LABELS[alert.intel_type] || alert.intel_type
  return (
    <button
      onClick={onClick}
      className="w-full text-left flex items-start gap-2.5 px-4 py-2.5 hover:bg-[#fafafa] transition-colors border-b border-[#f5f5f5] last:border-b-0"
    >
      {/* Type dot */}
      <span className="mt-1 flex-shrink-0 w-1.5 h-1.5 rounded-full" style={{ background: color }} />
      <div className="flex-1 min-w-0">
        {/* Headline */}
        <p className="text-[11px] text-[#111] leading-snug font-medium line-clamp-2">
          {alert.headline}
        </p>
        {/* Meta row */}
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-[9px] font-semibold uppercase tracking-wider" style={{ color }}>
            {label}
          </span>
          {alert.entity_name && (
            <span className="text-[9px] text-[#aaa]">{alert.entity_name}</span>
          )}
          {alert.iso2 && (
            <span className="text-[9px] text-[#aaa] font-mono">{alert.iso2}</span>
          )}
          <span className="text-[9px] text-[#ccc] ml-auto flex-shrink-0">
            {timeAgo(alert.occurred_at)}
          </span>
        </div>
      </div>
      {/* Importance badge */}
      <span
        className="flex-shrink-0 text-[8px] font-bold uppercase tracking-wider px-1 py-0.5 border mt-0.5"
        style={{ borderColor: color, color }}
      >
        {alert.importance >= 5 ? 'CRITICAL' : 'HIGH'}
      </span>
    </button>
  )
}

export default function NavBar() {
  const navigate  = useNavigate()
  const token     = localStorage.getItem('cl_token')
  const [health, setHealth]   = useState(null)
  const [bellOpen, setBellOpen] = useState(false)
  const bellRef   = useRef(null)

  const { alerts, unread, markRead } = useAlerts(token)
  const { watchedIds }               = useWatchlist()

  useEffect(() => {
    api.health().then(h => { setHealth(h) }).catch(() => {})
    const id = setInterval(() => api.health().then(setHealth).catch(() => {}), 20000)
    return () => clearInterval(id)
  }, [])

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e) {
      if (bellRef.current && !bellRef.current.contains(e.target)) {
        setBellOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  function handleBellToggle() {
    if (!bellOpen) markRead()
    setBellOpen(v => !v)
  }

  function handleAlertClick(alert) {
    setBellOpen(false)
    navigate(alertNavTarget(alert.intel_type))
  }

  function handleLogout() {
    localStorage.removeItem('cl_token')
    navigate('/')
    window.location.reload()
  }

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white border-b border-[#e0e0e0]">
      <div className="max-w-6xl mx-auto px-6 flex items-center h-12 gap-0">

        {/* Wordmark */}
        <NavLink to="/" className="flex items-center gap-2.5 mr-8">
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <rect x="1" y="1" width="6" height="6" stroke="#111" strokeWidth="1.25"/>
            <rect x="11" y="11" width="6" height="6" stroke="#111" strokeWidth="1.25"/>
            <line x1="7" y1="4" x2="11" y2="4" stroke="#111" strokeWidth="1.25"/>
            <line x1="11" y1="4" x2="11" y2="11" stroke="#111" strokeWidth="1.25"/>
          </svg>
          <span className="text-sm font-bold tracking-tight text-[#111] uppercase">
            Capital Lens
          </span>
        </NavLink>

        {/* Nav links */}
        <div className="flex items-center">
          {links.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `px-3 h-12 flex items-center gap-1.5 text-xs font-medium uppercase tracking-[0.06em] border-b-2 transition-all duration-200 ${
                  isActive
                    ? 'border-[#111] text-[#111]'
                    : 'border-transparent text-[#999] hover:text-[#111] hover:border-[#ccc]'
                }`
              }
            >
              {label}
              {to === '/watchlist' && watchedIds.length > 0 && (
                <span className="text-[9px] font-bold font-mono bg-[#f0a500] text-white rounded-full px-1 leading-none py-0.5">
                  {watchedIds.length}
                </span>
              )}
            </NavLink>
          ))}
        </div>

        {/* Right side */}
        <div className="ml-auto flex items-center gap-4">

          {/* Health stats */}
          {health && (
            <div className="flex items-center gap-4 text-[10px] font-medium uppercase tracking-[0.08em]">
              <span className="text-[#999]">
                <span className="font-mono font-bold text-[#111] text-xs">{health.events}</span>
                {' '}events
              </span>
              {health.pending > 0 ? (
                <span className="flex items-center gap-1.5 text-[#999]">
                  <span className="w-1.5 h-1.5 border border-[#999] rotate-45 inline-block" />
                  <span className="font-mono text-[#666]">{health.pending}</span> pending
                </span>
              ) : health.enriched > 0 ? (
                <span className="flex items-center gap-1.5 text-[#999]">
                  <span className="w-1.5 h-1.5 bg-[#111] rotate-45 inline-block" />
                  enriched
                </span>
              ) : null}
            </div>
          )}

          {/* Alert bell */}
          <div className="relative" ref={bellRef}>
            <button
              onClick={handleBellToggle}
              className="flex items-center justify-center w-8 h-8 hover:bg-[#f5f5f5] transition-colors"
              aria-label="Alerts"
            >
              <BellIcon unread={unread} />
            </button>

            {/* Dropdown panel */}
            {bellOpen && (
              <div className="absolute right-0 top-full mt-1 w-80 bg-white border border-[#e0e0e0] shadow-lg z-50">
                {/* Header */}
                <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#e0e0e0]">
                  <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[#111]">
                    Critical Alerts
                  </span>
                  {alerts.length > 0 && (
                    <span className="text-[9px] text-[#999]">Last 24 h · importance ≥ 4</span>
                  )}
                </div>

                {/* Alert list */}
                <div className="max-h-80 overflow-y-auto">
                  {alerts.length === 0 ? (
                    <p className="text-center py-8 text-[10px] text-[#ccc] uppercase tracking-widest">
                      No critical alerts
                    </p>
                  ) : (
                    alerts.slice(0, 15).map(a => (
                      <AlertRow
                        key={a.id}
                        alert={a}
                        onClick={() => handleAlertClick(a)}
                      />
                    ))
                  )}
                </div>

                {/* Footer */}
                {alerts.length > 0 && (
                  <div className="border-t border-[#f0f0f0] px-4 py-2 flex items-center justify-between">
                    <span className="text-[9px] text-[#ccc]">
                      {alerts.length} alert{alerts.length !== 1 ? 's' : ''} · updates every 60 s
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Auth */}
          {token ? (
            <div className="flex items-center gap-4">
              <NavLink
                to="/settings"
                className={({ isActive }) =>
                  `text-[10px] font-medium uppercase tracking-[0.08em] transition-colors ${
                    isActive ? 'text-[#111]' : 'text-[#999] hover:text-[#111]'
                  }`
                }
              >
                Settings
              </NavLink>
              <button
                onClick={handleLogout}
                className="text-[10px] font-medium uppercase tracking-[0.08em] text-[#999] hover:text-[#111] transition-colors"
              >
                Log out
              </button>
            </div>
          ) : (
            <NavLink
              to="/login"
              className="px-3 py-1.5 text-[10px] font-medium uppercase tracking-[0.08em] border border-[#111] text-[#111] hover:bg-[#111] hover:text-white transition-all duration-200"
            >
              Sign in
            </NavLink>
          )}
        </div>
      </div>

      {/* Enrichment scan bar */}
      {health?.pending > 0 && <ScanBar />}
    </nav>
  )
}
