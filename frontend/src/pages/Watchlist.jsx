import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import EntityAvatar from '../components/EntityAvatar'
import { api } from '../lib/api'
import { formatAmount, timeAgo } from '../lib/format'
import { useWatchlist } from '../hooks/useWatchlist'

function StarIcon({ filled }) {
  return (
    <svg width="13" height="13" viewBox="0 0 13 13" fill={filled ? 'currentColor' : 'none'}>
      <path
        d="M6.5 1L8.04 4.5L12 5.18L9.25 7.87L9.93 11.85L6.5 10.05L3.07 11.85L3.75 7.87L1 5.18L4.96 4.5L6.5 1Z"
        stroke="currentColor" strokeWidth="1.25" strokeLinejoin="round"
      />
    </svg>
  )
}

export default function Watchlist() {
  const navigate = useNavigate()
  const { watchedIds, toggle, isWatched } = useWatchlist()
  const [entities, setEntities] = useState([])
  const [loading, setLoading]   = useState(true)

  useEffect(() => {
    if (watchedIds.length === 0) {
      setEntities([])
      setLoading(false)
      return
    }
    setLoading(true)
    api.getEntities()
      .then(all => setEntities(all.filter(e => watchedIds.includes(e.id))))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [watchedIds.join(',')])

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">

      {/* Header */}
      <div className="pb-6 mb-8 border-b border-[#e0e0e0] flex items-end justify-between">
        <div>
          <p className="label text-[#999] mb-1">Personal</p>
          <h1 className="text-2xl font-bold tracking-tight text-[#111]">Watchlist</h1>
          <p className="text-xs text-[#999] font-light mt-1">
            {watchedIds.length === 0 ? 'No entities starred' : `${watchedIds.length} starred`}
          </p>
        </div>
        <Link
          to="/entities"
          className="text-[10px] font-medium uppercase tracking-[0.08em] text-[#999] hover:text-[#111] border border-[#e0e0e0] hover:border-[#111] px-3 py-1.5 transition-colors"
        >
          Browse entities
        </Link>
      </div>

      {/* Empty state */}
      {!loading && watchedIds.length === 0 && (
        <div className="text-center py-24">
          <div className="inline-flex items-center justify-center w-10 h-10 border border-[#e0e0e0] mb-4">
            <svg width="16" height="16" viewBox="0 0 13 13" fill="none" className="text-[#ccc]">
              <path
                d="M6.5 1L8.04 4.5L12 5.18L9.25 7.87L9.93 11.85L6.5 10.05L3.07 11.85L3.75 7.87L1 5.18L4.96 4.5L6.5 1Z"
                stroke="currentColor" strokeWidth="1.25" strokeLinejoin="round"
              />
            </svg>
          </div>
          <p className="text-xs text-[#999] uppercase tracking-[0.1em] mb-1">Watchlist empty</p>
          <p className="text-[11px] text-[#bbb] font-light mt-1 mb-6">
            Star entities from the directory or their profile pages
          </p>
          <Link
            to="/entities"
            className="text-[10px] font-semibold uppercase tracking-[0.08em] px-4 py-2 border border-[#111] text-[#111] hover:bg-[#111] hover:text-white transition-all"
          >
            Go to Entities
          </Link>
        </div>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-px bg-[#e0e0e0]">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="bg-white p-4 h-20 animate-pulse">
              <div className="flex gap-3">
                <div className="w-9 h-9 bg-[#f0f0f0]" />
                <div className="flex-1 space-y-2 pt-1">
                  <div className="h-2.5 w-28 bg-[#f0f0f0]" />
                  <div className="h-2 w-16 bg-[#f5f5f5]" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Entity grid */}
      {!loading && entities.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-px bg-[#e0e0e0]">
          {entities.map(en => (
            <WatchlistCard
              key={en.id}
              entity={en}
              onNavigate={() => navigate(`/entities/${en.id}`)}
              onUnstar={() => toggle(en.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function WatchlistCard({ entity: en, onNavigate, onUnstar }) {
  return (
    <div className="bg-white relative group hover:bg-[#fafafa] transition-colors duration-200">
      <button onClick={onNavigate} className="w-full p-4 text-left pr-10">
        <div className="flex items-center gap-3">
          <EntityAvatar name={en.name} size="md" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-bold text-[#111] truncate group-hover:underline">{en.name}</p>
            <div className="flex items-center gap-2 mt-0.5">
              <p className="text-[10px] font-medium uppercase tracking-[0.06em] text-[#999]">{en.sector}</p>
              {en.type === 'individual' && (
                <span className="text-[9px] text-[#bbb] uppercase tracking-wider">· Person</span>
              )}
            </div>
          </div>
          <div className="text-right flex-shrink-0 ml-2">
            {en.last_price ? (
              <p className="text-xs font-mono font-bold text-[#111]">
                ${en.last_price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </p>
            ) : en.net_worth ? (
              <p className="text-xs font-mono font-bold text-[#111]">
                {formatAmount(en.net_worth).replace(' USD', '')}
              </p>
            ) : null}
            {en.price_updated_at && (
              <p className="text-[9px] text-[#ccc] mt-0.5">{timeAgo(en.price_updated_at)}</p>
            )}
          </div>
        </div>
      </button>
      {/* Unstar button */}
      <button
        onClick={onUnstar}
        className="absolute top-1/2 -translate-y-1/2 right-3 p-1.5 transition-colors"
        style={{ color: '#f0a500' }}
        title="Remove from watchlist"
      >
        <StarIcon filled={true} />
      </button>
    </div>
  )
}
