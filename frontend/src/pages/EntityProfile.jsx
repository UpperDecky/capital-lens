import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import EntityAvatar from '../components/EntityAvatar'
import EventCard from '../components/EventCard'
import { api } from '../lib/api'
import { formatAmount, timeAgo } from '../lib/format'

export default function EntityProfile() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [entity, setEntity] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState(null)

  useEffect(() => {
    setLoading(true)
    api.getEntity(id).then(setEntity).catch(e => setError(e.message)).finally(() => setLoading(false))
  }, [id])

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
            <h1 className="text-xl font-bold tracking-tight text-[#111]">{entity.name}</h1>
            {entity.description && (
              <p className="text-xs font-light text-[#666] mt-2 leading-relaxed">{entity.description}</p>
            )}
          </div>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-3 divide-x divide-[#e0e0e0]">
          {[
            { label: entity.type === 'individual' ? 'Net Worth' : 'Market Cap', value: formatAmount(entity.net_worth) || '—', mono: true },
            { label: 'Events Tracked',  value: entity.events?.length || 0,   mono: false },
            { label: 'Capital Moved',   value: totalCapital > 0 ? formatAmount(totalCapital) : '—', mono: true },
          ].map(stat => (
            <div key={stat.label} className="p-5">
              <p className="label text-[#999] mb-1">{stat.label}</p>
              <p className={`text-lg font-bold text-[#111] ${stat.mono ? 'font-mono' : ''}`}>{stat.value}</p>
            </div>
          ))}
        </div>

        {/* Live price strip — only shown when Alpha Vantage data is available */}
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
