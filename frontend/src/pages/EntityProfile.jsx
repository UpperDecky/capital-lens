import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import EntityAvatar from '../components/EntityAvatar'
import EventCard from '../components/EventCard'
import PriceChart from '../components/PriceChart'
import { api } from '../lib/api'
import { formatAmount, timeAgo } from '../lib/format'
import { useWatchlist } from '../hooks/useWatchlist'

function StarIcon({ filled }) {
  return (
    <svg width="14" height="14" viewBox="0 0 13 13" fill={filled ? 'currentColor' : 'none'}>
      <path
        d="M6.5 1L8.04 4.5L12 5.18L9.25 7.87L9.93 11.85L6.5 10.05L3.07 11.85L3.75 7.87L1 5.18L4.96 4.5L6.5 1Z"
        stroke="currentColor" strokeWidth="1.25" strokeLinejoin="round"
      />
    </svg>
  )
}

export default function EntityProfile() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [entity, setEntity]         = useState(null)
  const [loading, setLoading]       = useState(true)
  const [error, setError]           = useState(null)
  const [chartData, setChartData]   = useState(null)
  const [chartDays, setChartDays]   = useState(30)
  const { toggle, isWatched }       = useWatchlist()

  useEffect(() => {
    setLoading(true)
    api.getEntity(id).then(setEntity).catch(e => setError(e.message)).finally(() => setLoading(false))
  }, [id])

  useEffect(() => {
    if (!entity?.ticker) return
    setChartData(null)
    api.getEntityTimeseries(id, chartDays)
      .then(setChartData)
      .catch(() => {})
  }, [id, entity?.ticker, chartDays])

  if (loading) return (
    <div className="max-w-3xl mx-auto px-6 py-10 animate-pulse space-y-px">
      <div className="bg-white border border-[#e0e0e0] h-32" />
      <div className="bg-white border border-[#e0e0e0] h-64" />
    </div>
  )

  if (error) return (
    <div className="max-w-3xl mx-auto px-6 py-10">
      <div className="border border-[#111] p-4">
        <p className="label mb-1">Error</p>
        <p className="text-xs font-light">{error}</p>
      </div>
      <button onClick={() => navigate(-1)} className="mt-4 text-xs text-[#999] hover:text-[#111] uppercase tracking-[0.06em]">← Back</button>
    </div>
  )

  if (!entity) return null

  const totalCapital  = entity.events?.reduce((s, e) => s + (e.amount || 0), 0) || 0
  const enrichedCount = entity.events?.filter(e => e.plain_english).length || 0

  return (
    <div className="max-w-3xl mx-auto px-6 py-10">
      <button onClick={() => navigate(-1)}
        className="text-[10px] font-medium uppercase tracking-[0.08em] text-[#999] hover:text-[#111] transition-colors mb-6 flex items-center gap-1">
        ← Back
      </button>

      {/* Profile card */}
      <div className="bg-white border border-[#e0e0e0] mb-px">
        {/* Top: avatar + info */}
        <div className="flex items-stretch border-b border-[#e0e0e0]">
          <div className="p-6 border-r border-[#e0e0e0]">
            <EntityAvatar name={entity.name} size="lg" />
          </div>
          <div className="flex-1 p-6">
            <p className="label text-[#999] mb-1">
              {entity.type === 'company' ? 'Company' : 'Individual'} · {entity.sector}
            </p>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-[#111]">{entity.name}</h1>
              <button
                onClick={() => toggle(entity.id)}
                className="transition-colors mt-0.5"
                style={{ color: isWatched(entity.id) ? '#f0a500' : '#ddd' }}
                title={isWatched(entity.id) ? 'Remove from watchlist' : 'Add to watchlist'}
              >
                <StarIcon filled={isWatched(entity.id)} />
              </button>
            </div>
            {entity.description && (
              <p className="text-xs font-light text-[#666] mt-2 leading-relaxed">{entity.description}</p>
            )}
          </div>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-3 divide-x divide-[#e0e0e0]">
          <div className="p-5">
            <p className="label text-[#999] mb-1">
              {entity.type === 'individual' ? 'Est. Net Worth' : 'Market Cap'}
            </p>
            <p className="text-lg font-bold text-[#111] font-mono">
              {formatAmount(entity.net_worth) || '—'}
            </p>
            {/* Data freshness row */}
            <div className="flex items-center gap-1.5 mt-1.5">
              {entity.net_worth_source && entity.net_worth_source !== 'seed_initial' ? (
                <span className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#22c55e]" />
                  <span className="text-[9px] text-[#22c55e] font-medium uppercase tracking-wider">Live</span>
                </span>
              ) : (
                <span className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#f59e0b]" />
                  <span className="text-[9px] text-[#f59e0b] font-medium uppercase tracking-wider">Estimate</span>
                </span>
              )}
              {entity.net_worth_updated_at && (
                <span className="text-[9px] text-[#bbb]">
                  {timeAgo(entity.net_worth_updated_at)}
                </span>
              )}
            </div>
          </div>
          <div className="p-5">
            <p className="label text-[#999] mb-1">Events Tracked</p>
            <p className="text-lg font-bold text-[#111]">{entity.events?.length || 0}</p>
          </div>
          <div className="p-5">
            <p className="label text-[#999] mb-1">Capital Moved</p>
            <p className="text-lg font-bold text-[#111] font-mono">
              {totalCapital > 0 ? formatAmount(totalCapital) : '—'}
            </p>
          </div>
        </div>

        {/* Live price strip */}
        {entity.last_price && (
          <div className="border-t border-[#e0e0e0] px-5 py-3 flex items-center gap-4 bg-[#fafafa]">
            <span className="label text-[#999]">Live Price</span>
            <span className="font-mono text-sm font-bold text-[#111]">
              ${entity.last_price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
            {entity.ticker && (
              <span className="label border border-[#e0e0e0] px-1.5 py-px text-[#666]">{entity.ticker}</span>
            )}
            {entity.price_updated_at && (
              <span className="text-[10px] text-[#ccc] font-light ml-auto">
                Updated {timeAgo(entity.price_updated_at)}
              </span>
            )}
          </div>
        )}

        {/* Price chart — only for entities with a ticker */}
        {entity.ticker && (
          <div className="border-t border-[#e0e0e0]">
            {/* Chart header */}
            <div className="flex items-center justify-between px-5 pt-3 pb-1">
              <span className="label text-[#999]">Price History</span>
              <div className="flex items-center gap-1">
                {[7, 30, 90].map(d => (
                  <button
                    key={d}
                    onClick={() => setChartDays(d)}
                    className="text-[9px] font-semibold uppercase tracking-wider px-2 py-1 transition-colors"
                    style={chartDays === d
                      ? { color: '#111', borderBottom: '1.5px solid #111' }
                      : { color: '#bbb' }}
                  >
                    {d}D
                  </button>
                ))}
              </div>
            </div>

            {/* Chart body */}
            <div className="px-2 pb-3">
              {chartData ? (
                <PriceChart data={chartData} height={150} />
              ) : (
                <div className="h-[150px] flex items-center justify-center text-[10px] text-[#ccc] uppercase tracking-widest animate-pulse">
                  Loading chart…
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Events */}
      <div className="mt-8 mb-4 flex items-center gap-4">
        <p className="label text-[#999]">Recent Events</p>
        <div className="flex-1 h-px bg-[#e0e0e0]" />
        {enrichedCount > 0 && <p className="label text-[#999]">{enrichedCount} enriched</p>}
      </div>

      {entity.events?.length === 0 ? (
        <p className="text-center py-12 text-[10px] uppercase tracking-[0.1em] text-[#bbb]">No events tracked</p>
      ) : (
        <div className="space-y-px">
          {entity.events?.map(ev => (
            <EventCard
              key={ev.id}
              event={{ ...ev, entity_name: entity.name, entity_type: entity.type, entity_sector: entity.sector }}
              onTagClick={tag => navigate(`/?tag=${encodeURIComponent(tag)}`)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
