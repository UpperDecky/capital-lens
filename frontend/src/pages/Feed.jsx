import { useState, useEffect, useCallback, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import EventCard from '../components/EventCard'
import LoadMore from '../components/LoadMore'
import AnalysisPanel from '../components/AnalysisPanel'
import { FlowEmpty, ScanBar } from '../components/Illustrations'
import { api } from '../lib/api'

const SECTORS = [
  'Technology', 'Finance', 'E-Commerce', 'Energy', 'Healthcare',
  'Defense', 'Aerospace', 'Retail', 'Automotive', 'Government',
]
const TYPES = [
  { value: 'filing',              label: 'SEC Filing'     },
  { value: 'insider_sale',        label: 'Insider Trade'  },
  { value: 'congressional_trade', label: 'Congress'       },
  { value: 'acquisition',         label: 'Acquisition'    },
  { value: 'news',                label: 'News'           },
]
const IMPORTANCE_OPTIONS = [
  { value: '',  label: 'All Priority'      },
  { value: '4', label: 'High+ (4–5)'       },
  { value: '5', label: 'Critical Only (5)' },
  { value: '3', label: 'Notable+ (3–5)'    },
]

function Skeleton() {
  return (
    <div className="bg-white border border-[#e0e0e0] animate-pulse">
      <div className="flex items-stretch border-b border-[#e0e0e0]">
        <div className="w-16 h-16 bg-[#f0f0f0] border-r border-[#e0e0e0]" />
        <div className="flex-1 px-4 py-3 space-y-2">
          <div className="h-3 w-32 bg-[#f0f0f0]" />
          <div className="h-2 w-20 bg-[#f5f5f5]" />
        </div>
      </div>
      <div className="px-4 py-3 border-b border-[#e0e0e0]">
        <div className="h-3 w-full bg-[#f0f0f0]" />
      </div>
      <div className="p-4 space-y-2">
        <div className="h-2 w-16 bg-[#f0f0f0]" />
        <div className="h-3 w-5/6 bg-[#f5f5f5]" />
        <div className="grid grid-cols-2 gap-0 mt-3">
          <div className="h-20 bg-[#f5f5f5]" />
          <div className="h-20 bg-[#f5f5f5]" />
        </div>
      </div>
    </div>
  )
}

/** Small date input that clears on ×-click */
function DateInput({ label, value, onChange }) {
  return (
    <div className="flex items-center gap-0 border border-[#e0e0e0]">
      <span className="px-2 py-1.5 text-[10px] font-medium uppercase tracking-[0.08em] text-[#999] bg-[#fafafa] border-r border-[#e0e0e0] select-none whitespace-nowrap">
        {label}
      </span>
      <input
        type="date"
        value={value}
        onChange={e => onChange(e.target.value)}
        className="px-2 py-1.5 text-[10px] font-mono text-[#111] bg-white focus:outline-none w-32 cursor-pointer"
      />
      {value && (
        <button
          onClick={() => onChange('')}
          className="px-2 py-1.5 text-[10px] text-[#bbb] hover:text-[#111] transition-colors border-l border-[#e0e0e0]"
          title="Clear"
        >
          ×
        </button>
      )}
    </div>
  )
}

export default function Feed() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [events, setEvents]           = useState([])
  const [page, setPage]               = useState(1)
  const [total, setTotal]             = useState(0)
  const [hasMore, setHasMore]         = useState(false)
  const [loading, setLoading]         = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError]             = useState(null)
  const [health, setHealth]           = useState(null)
  const [enriching, setEnriching]     = useState(false)
  const [ingesting, setIngesting]     = useState(false)
  const [selectedEvent, setSelectedEvent] = useState(null)
  const pollRef = useRef(null)

  const sector       = searchParams.get('sector')       || ''
  const type         = searchParams.get('type')         || ''
  const activeTag    = searchParams.get('tag')          || ''
  const dateFrom     = searchParams.get('date_from')    || ''
  const dateTo       = searchParams.get('date_to')      || ''
  const minImportance = searchParams.get('min_importance') || ''

  const fetchHealth = useCallback(() =>
    api.health().then(setHealth).catch(() => {}), [])

  useEffect(() => { fetchHealth() }, [fetchHealth])

  function setParam(key, val) {
    const p = new URLSearchParams(searchParams)
    if (val) p.set(key, val); else p.delete(key)
    if (key !== 'tag') p.delete('tag')
    setSearchParams(p); setPage(1); setEvents([])
  }
  function setDateFrom(val) {
    const p = new URLSearchParams(searchParams)
    if (val) p.set('date_from', val); else p.delete('date_from')
    setSearchParams(p); setPage(1); setEvents([])
  }
  function setDateTo(val) {
    const p = new URLSearchParams(searchParams)
    if (val) p.set('date_to', val); else p.delete('date_to')
    setSearchParams(p); setPage(1); setEvents([])
  }
  function handleTagClick(tag) {
    const p = new URLSearchParams(searchParams)
    if (activeTag === tag) p.delete('tag'); else p.set('tag', tag)
    setSearchParams(p); setPage(1); setEvents([])
  }
  function clearFilters() {
    setSearchParams({}); setPage(1); setEvents([])
  }

  const fetchPage = useCallback(async (pg, replace = false) => {
    try {
      const params = { page: pg, limit: 20 }
      if (sector)       params.sector        = sector
      if (type)         params.type          = type
      if (dateFrom)     params.date_from     = dateFrom
      if (dateTo)       params.date_to       = dateTo
      if (minImportance) params.min_importance = minImportance
      const data = await api.getFeed(params)
      setEvents(prev => replace ? data.events : [...prev, ...data.events])
      setTotal(data.total); setHasMore(data.has_more); setPage(pg); setError(null)
    } catch (e) { setError(e.message) }
  }, [sector, type, dateFrom, dateTo, minImportance])

  useEffect(() => {
    setLoading(true); setEvents([])
    fetchPage(1, true).finally(() => setLoading(false))
  }, [fetchPage])

  // Auto-poll every 15s
  useEffect(() => {
    pollRef.current = setInterval(() => {
      fetchPage(1, true); fetchHealth()
    }, 15000)
    return () => clearInterval(pollRef.current)
  }, [fetchPage, fetchHealth])

  // Keep selected event in sync when events list refreshes
  useEffect(() => {
    if (selectedEvent) {
      const updated = events.find(e => e.id === selectedEvent.id)
      if (updated) setSelectedEvent(updated)
    }
  }, [events]) // eslint-disable-line

  const handleLoadMore = useCallback(async () => {
    if (loadingMore || !hasMore) return
    setLoadingMore(true)
    await fetchPage(page + 1)
    setLoadingMore(false)
  }, [loadingMore, hasMore, page, fetchPage])

  async function handleEnrich() {
    setEnriching(true)
    await api.adminEnrich().catch(() => {})
    let polls = 0
    const iv = setInterval(async () => {
      await fetchPage(1, true); await fetchHealth(); polls++
      if (polls >= 12) { clearInterval(iv); setEnriching(false) }
    }, 5000)
  }

  async function handleIngest() {
    setIngesting(true)
    await api.adminIngest().catch(() => {})
    setTimeout(async () => {
      await fetchPage(1, true); await fetchHealth(); setIngesting(false)
    }, 8000)
  }

  function handleSelectEvent(ev) {
    setSelectedEvent(prev => prev?.id === ev.id ? null : ev)
  }

  const pending = health?.pending ?? 0
  const hasFilters = sector || type || activeTag || dateFrom || dateTo || minImportance

  // Describe the active date filter in human-readable form
  function dateFilterLabel() {
    if (dateFrom && dateTo) return `${dateFrom} → ${dateTo}`
    if (dateFrom) return `After ${dateFrom}`
    if (dateTo)   return `Before ${dateTo}`
    return null
  }

  return (
    <div className="flex h-full overflow-hidden">

      {/* ── Feed column ── */}
      <div className={`flex flex-col flex-shrink-0 overflow-y-auto transition-all duration-300 ${
        selectedEvent ? 'w-[56%] border-r border-[#e0e0e0]' : 'w-full max-w-3xl mx-auto'
      }`}>
        <div className="px-6 py-8">

          {/* Page header */}
          <div className="flex items-end justify-between mb-6 pb-6 border-b border-[#e0e0e0]">
            <div>
              <p className="label text-[#999] mb-1">Capital Lens</p>
              <h1 className="text-2xl font-bold tracking-tight text-[#111]">Intelligence Feed</h1>
              {health && (
                <p className="text-xs text-[#999] font-light mt-1">
                  {total > 0 ? `${total} events` : `${health.events} events`}
                  {health.enriched > 0 && ` · ${health.enriched} enriched`}
                  {pending > 0 && ` · ${pending} queued`}
                </p>
              )}
            </div>
            <div className="flex gap-2">
              <button onClick={handleIngest} disabled={ingesting}
                className="btn flex items-center gap-2 disabled:opacity-40">
                {ingesting
                  ? <><span className="w-3 h-3 border border-current border-t-transparent rounded-full animate-spin" />Fetching</>
                  : <>Fetch data</>}
              </button>
              <button onClick={handleEnrich} disabled={enriching || pending === 0}
                className="btn btn-primary flex items-center gap-2 disabled:opacity-40">
                {enriching
                  ? <><span className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin" />Enriching</>
                  : pending > 0 ? `Enrich ${pending}` : 'All enriched'}
              </button>
            </div>
          </div>

          {/* Scan bar when enrichment pending */}
          {pending > 0 && <ScanBar />}

          {/* ── Date range filter ── */}
          <div className="mb-3">
            <p className="label text-[#bbb] mb-2">Date Range</p>
            <div className="flex flex-wrap items-center gap-2">
              <DateInput label="From" value={dateFrom} onChange={setDateFrom} />
              <DateInput label="To"   value={dateTo}   onChange={setDateTo}   />
              {(dateFrom || dateTo) && (
                <button
                  onClick={() => { setDateFrom(''); setDateTo('') }}
                  className="px-3 py-1.5 text-[10px] font-medium uppercase tracking-[0.08em] border border-[#e0e0e0] text-[#999] hover:border-[#111] hover:text-[#111] transition-all duration-200"
                >
                  Clear dates
                </button>
              )}
            </div>
            {dateFilterLabel() && (
              <p className="text-[10px] text-[#999] font-mono mt-1.5">
                Showing: {dateFilterLabel()}
              </p>
            )}
          </div>

          {/* ── Sector, type, and importance filters ── */}
          <div className="flex flex-wrap gap-2 mb-6">
            <select value={sector} onChange={e => setParam('sector', e.target.value)}
              className="px-3 py-1.5 text-xs font-medium uppercase tracking-[0.06em] border border-[#e0e0e0] bg-white text-[#666] focus:border-[#111] transition-colors duration-200 cursor-pointer">
              <option value="">All Sectors</option>
              {SECTORS.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
            <select value={type} onChange={e => setParam('type', e.target.value)}
              className="px-3 py-1.5 text-xs font-medium uppercase tracking-[0.06em] border border-[#e0e0e0] bg-white text-[#666] focus:border-[#111] transition-colors duration-200 cursor-pointer">
              <option value="">All Types</option>
              {TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
            <select value={minImportance} onChange={e => setParam('min_importance', e.target.value)}
              className="px-3 py-1.5 text-xs font-medium uppercase tracking-[0.06em] border border-[#e0e0e0] bg-white text-[#666] focus:border-[#111] transition-colors duration-200 cursor-pointer">
              {IMPORTANCE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
            {hasFilters && (
              <button onClick={clearFilters}
                className="px-3 py-1.5 text-xs font-medium uppercase tracking-[0.06em] border border-[#e0e0e0] text-[#999] hover:border-[#111] hover:text-[#111] transition-all duration-200">
                Clear all
              </button>
            )}
          </div>

          {/* Error */}
          {error && (
            <div className="border border-[#111] p-4 mb-6 bg-[#fafafa]">
              <p className="label mb-1">Connection Error</p>
              <p className="text-xs font-light text-[#444]">
                Cannot reach backend on port 8000. Is uvicorn running?
              </p>
            </div>
          )}

          {/* Content */}
          {loading ? (
            <div className="space-y-px">
              <Skeleton /><Skeleton /><Skeleton />
            </div>
          ) : events.length === 0 ? (
            <div className="py-16 flex flex-col items-center gap-6">
              <FlowEmpty size={120} />
              <div className="text-center">
                <p className="label mb-1">No events</p>
                <p className="text-xs font-light text-[#999]">
                  {hasFilters ? 'No events match the current filters — try widening the date range or clearing filters.' : 'Fetch fresh data from the top-right.'}
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-px">
              {events.map(ev => (
                <EventCard
                  key={ev.id}
                  event={ev}
                  onTagClick={handleTagClick}
                  activeTag={activeTag}
                  selected={selectedEvent?.id === ev.id}
                  onSelect={handleSelectEvent}
                  compact={!!selectedEvent}
                />
              ))}
            </div>
          )}

          <LoadMore hasMore={hasMore} loading={loadingMore} onLoadMore={handleLoadMore} />
        </div>
      </div>

      {/* ── Analysis panel ── */}
      {selectedEvent && (
        <div className="flex-1 overflow-hidden">
          <AnalysisPanel event={selectedEvent} onClose={() => setSelectedEvent(null)} />
        </div>
      )}
    </div>
  )
}
