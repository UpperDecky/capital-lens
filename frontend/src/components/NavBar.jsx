import { NavLink, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { ScanBar } from './Illustrations'

const links = [
  { to: '/',         label: 'Feed'     },
  { to: '/entities', label: 'Entities' },
  { to: '/flowmap',  label: 'Flow Map' },
  { to: '/themes',   label: 'Themes'   },
  { to: '/search',   label: 'Search'   },
]

export default function NavBar() {
  const navigate = useNavigate()
  const token = localStorage.getItem('cl_token')
  const [health, setHealth]   = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    api.health().then(h => { setHealth(h) }).catch(() => {})
    const id = setInterval(() => api.health().then(setHealth).catch(() => {}), 20000)
    return () => clearInterval(id)
  }, [])

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
          {/* Logo: abstract routing mark */}
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
                `px-3 h-12 flex items-center text-xs font-medium uppercase tracking-[0.06em] border-b-2 transition-all duration-200 ${
                  isActive
                    ? 'border-[#111] text-[#111]'
                    : 'border-transparent text-[#999] hover:text-[#111] hover:border-[#ccc]'
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </div>

        {/* Stats */}
        {health && (
          <div className="ml-auto flex items-center gap-4 text-[10px] font-medium uppercase tracking-[0.08em]">
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

        {/* Auth */}
        {token ? (
          <button
            onClick={handleLogout}
            className="ml-4 text-[10px] font-medium uppercase tracking-[0.08em] text-[#999] hover:text-[#111] transition-colors"
          >
            Log out
          </button>
        ) : (
          <NavLink
            to="/login"
            className="ml-4 px-3 py-1.5 text-[10px] font-medium uppercase tracking-[0.08em] border border-[#111] text-[#111] hover:bg-[#111] hover:text-white transition-all duration-200"
          >
            Sign in
          </NavLink>
        )}
      </div>

      {/* Enrichment scan bar */}
      {health?.pending > 0 && <ScanBar />}
    </nav>
  )
}
