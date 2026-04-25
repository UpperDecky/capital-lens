import React, { useState, useEffect, useCallback, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import EventCard from '../components/EventCard'
import IntelCard from '../components/IntelCard'
import LoadMore from '../components/LoadMore'
import AnalysisPanel from '../components/AnalysisPanel'
import TierBadge from '../components/TierBadge'
import { FlowEmpty, ScanBar } from '../components/Illustrations'
import { api } from '../lib/api'

const SECTORS = [
  'Technology', 'Finance', 'E-Commerce', 'Energy', 'Healthcare',
  'Defense', 'Aerospace', 'Retail', 'Automotive', 'Government',
]
const TYPES = [
  { value: 'filing',              label: 'SEC Filing'    },
  { value: 'insider_sale',        label: 'Insider Trade' },
  { value: 'congressional_trade', label: 'Congress'      },
  { value: 'acquisition',         label: 'Acquisition'   },
  { value: 'news',                label: 'News'          },
]
const IMPORTANCE_OPTIONS = [
  { value: '',  label: 'All Priority'      },
  { value: '4', label: 'High+ (4-5)'       },
  { value: '5', label: 'Critical Only (5)' },
  { value: '3', label: 'Notable+ (3-5)'    },
]
const INTEL_TYPES = [
  { value: '',           label: 'All Intel'      },
  { value: 'geo_event',  label: 'Geopolitical'   },
  { value: 'adsb',       label: 'Aircraft'       },
  { value: 'maritime',   label: 'Maritime'       },
  { value: 'satellite',  label: 'Satellite'      },
  { value: 'prediction', label: 'Prediction Mkt' },
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

function IntelSkeleton() {
  return (
    <div className="bg-white border border-[#e0e0e0] animate-pulse flex">
      <div className="w-1 bg-[#e0e0e0] flex-shrink-0" />
      <div className="flex-1 px-4 py-3 space-y-2">
        <div className="flex gap-2">
          <div className="h-4 w-20 bg-[#f0f0f0]" />
          <div className="h-4 w-12 bg-[#f5f5f5]" />
        </div>
        <div className="h-3 w-full bg-[#f0f0f0]" />
        <div className="h-3 w-3/4 bg-[#f5f5f5]" />
        <div className="flex gap-3 mt-2">
          <div className="h-6 w-16 bg-[#f5f5f5]" />
          <div className="h-6 w-16 bg-[#f5f5f5]" />
        </div>
      </div>
    </div>
  )
}

function DownloadIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
      <line x1="5.5" y1="1" x2="5.5" y2="7.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
      <polyline points="2.5,5 5.5,8 8.5,5" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
      <line x1="1" y1="10" x2="10" y2="10" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
    </svg>
  )
}

function ExportMenu({ filters }) {
  const [open, setOpen] = React.useState(false)
  const ref = React.useRef(null)

  React.useEffect(() => {
    function handler(e) { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  function download(fmt) {
    const p = new URLSearchParams()
    p.set('format', fmt)
    if (filters.sector)        p.set('sector', filters.sector)
    if (filters.type)          p.set('type', filters.type)
    if (filters.dateFrom)      p.set('date_from', filters.dateFrom)
    if (filters.dateTo)        p.set('date_to', filters.dateTo)
    if (filters.minImportance) p.set('min_importance', filters.minImportance)
    if (filters.sort)          p.set('sort', filters.sort)
    window.location.href = `/feed/export?${p.toString()}`
    setOpen(false)
  }

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(v => !v)}
        className="btn flex items-center gap-1.5"
        title="Download current view"
      >
        <DownloadIcon /> Export
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-1 bg-white border border-[#e0e0e0] shadow-md z-20 min-w-[100px]">
          {['CSV', 'JSON'].map(fmt => (
            <button
              key={fmt}
              onClick={() => download(fmt.toLowerCase())}
              className="w-full text-left px-4 py-2.5 text-[10px] font-semibold uppercase tracking-[0.08em] text-[#444] hover:bg-[#fafafa] hover:text-[#111] transition-colors"
            >
              {fmt}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

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
        >
          x
        </button>
      )}
    </div>
  )
}

// ── Financial feed ────────────────────────────────────────────────────────────
function FinancialFeed({ health, onEnrich, onIngest, enriching, ingesting }) {
  const [searchParams, setSearchParams] = useSearchParams()
  const [events, setEvents]           = useState([])
  const [page, setPage]               = useState(1)
  const [total, setTotal]             = useState(0)
  const [hasMore, setHasMore]         = useState(false)
  const [loading, setLoading]         = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError]             = useState(null)
  const [selectedEvent, setSelectedEvent] = useState(null)
  const [tierInfo, setTierInfo]       = useState(null)
  const [limitReached, setLimitReached] = useState(null)
  const pollRef = useRef(null)

  const sector        = searchParams.get('sector')         || ''
  const type          = searchParams.get('type')           || ''
  const activeTag     = searchParams.get('tag')            || ''
  const dateFrom      = searchParams.get('date_from')      || ''
  const dateTo        = searchParams.get('date_to')        || ''
  const minImportance = searchParams.get('min_importance') || ''
  const sort          = searchParams.get('sort')           || 'top'

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
    const p = new URLSearchParams(searchParams)
    ;['sector','type','tag','date_from','date_to','min_importance'].forEach(k => p.delete(k))
    setSearchParams(p); setPage(1); setEvents([])
  }

  const fetchPage = useCallback(async (pg, replace = false) => {
    try {
      const params = { page: pg, limit: 20 }
      if (sector)        params.sector         = sector
      if (type)          params.type           = type
      if (dateFrom)      params.date_from      = dateFrom
      if (dateTo)        params.date_to        = dateTo
      if (minImportance) params.min_importance = minImportance
      if (sort)          params.sort           = sort
      const data = await api.getFeed(params)
      setEvents(prev => replace ? data.events : [...prev, ...data.events])
      setTotal(data.total); setHasMore(data.has_more); setPage(pg); setError(null)
      if (data.tier) {
        setTierInfo({ tier: data.tier, daily_remaining: data.daily_remaining, daily_limit: data.daily_limit, reset_at: data.reset_at })
        setLimitReached(null)
      }
    } catch (e) {
      if (e.status === 429) {
        setLimitReached(e.detail?.reset_at || null)
      } else {
        setError(e.message)
      }
    }
  }, [sector, type, dateFrom, dateTo, minImportance, sort])

  useEffect(() => {
    setLoading(true); setEvents([])
    fetchPage(1, true).finally(() => setLoading(false))
  }, [fetchPage])

  useEffect(() => {
    pollRef.current = setInterval(() => fetchPage(1, true), 15000)
    return () => clearInterval(pollRef.current)
  }, [fetchPage])

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

  const pending = health?.pending ?? 0
  const hasFilters = sector || type || activeTag || dateFrom || dateTo || minImportance

  function dateFilterLabel() {
    if (dateFrom && dateTo) return `${dateFrom} to ${dateTo}`
    if (dateFrom) return `After ${dateFrom}`
    if (dateTo)   return `Before ${dateTo}`
    return null
  }

  return (
    <div className="flex h-full overflow-hidden">
      <div className={`flex flex-col flex-shrink-0 overflow-y-auto transition-all duration-300 ${
        selectedEvent ? 'w-[56%] border-r border-[#e0e0e0]' : 'w-full max-w-3xl mx-auto'
      }`}>
        <div className="px-6 py-6">

          {/* Controls row */}
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-3">
              <p className="text-xs text-[#999]">
                {total > 0 ? `${total} events` : health ? `${health.events} events` : ''}
                {health?.enriched > 0 && ` · ${health.enriched} enriched`}
                {pending > 0 && ` · ${pending} queued`}
              </p>
              {tierInfo && (
                <TierBadge
                  tier={tierInfo.tier}
                  dailyRemaining={tierInfo.daily_remaining}
                  dailyLimit={tierInfo.daily_limit}
                  resetAt={tierInfo.reset_at}
                />
              )}
            </div>
            <div className="flex gap-2">
              <ExportMenu filters={{ sector, type, dateFrom, dateTo, minImportance, sort }} />
              <button onClick={onIngest} disabled={ingesting}
                className="btn flex items-center gap-2 disabled:opacity-40">
                {ingesting
                  ? <><span className="w-3 h-3 border border-current border-t-transparent rounded-full animate-spin"/>Fetching</>
                  : 'Fetch data'}
              </button>
              <button onClick={onEnrich} disabled={enriching || pending === 0}
                className="btn btn-primary flex items-center gap-2 disabled:opacity-40">
                {enriching
                  ? <><span className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin"/>Enriching</>
                  : pending > 0 ? `Enrich ${pending}` : 'All enriched'}
              </button>
            </div>
          </div>

          {/* Daily limit banner */}
          {limitReached && (
            <div className="border border-red-200 bg-red-50 px-4 py-3 mb-5 flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold text-red-700 mb-0.5">Daily limit reached</p>
                <p className="text-[11px] text-red-500">
                  You have used all 20 events for today.
                  {limitReached && ` Resets at ${new Date(limitReached).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} UTC.`}
                </p>
              </div>
              <a href="/settings" className="text-[10px] font-semibold uppercase tracking-[0.08em] text-red-600 border border-red-300 px-3 py-1.5 hover:bg-red-100 transition-colors whitespace-nowrap ml-4">
                Upgrade to Pro
              </a>
            </div>
          )}

          {/* Sort tabs */}
          <div className="flex mb-4 border-b border-[#e0e0e0]">
            {[['top','Top Headlines'],['recent','Most Recent']].map(([key, label]) => (
              <button key={key}
                onClick={() => { const p = new URLSearchParams(searchParams); p.set('sort', key); setSearchParams(p); setPage(1); setEvents([]) }}
                className={`px-4 py-2.5 text-xs font-medium uppercase tracking-[0.08em] border-b-2 -mb-px transition-colors ${
                  sort === key ? 'border-[#111] text-[#111]' : 'border-transparent text-[#999] hover:text-[#555]'
                }`}>{label}</button>
            ))}
          </div>

          {pending > 0 && <ScanBar />}

          {/* Date range */}
          <div className="mb-3">
            <p className="label text-[#bbb] mb-2">Date Range</p>
            <div className="flex flex-wrap items-center gap-2">
              <DateInput label="From" value={dateFrom} onChange={setDateFrom} />
              <DateInput label="To"   value={dateTo}   onChange={setDateTo}   />
              {(dateFrom || dateTo) && (
                <button onClick={() => { setDateFrom(''); setDateTo('') }}
                  className="px-3 py-1.5 text-[10px] font-medium uppercase tracking-[0.08em] border border-[#e0e0e0] text-[#999] hover:border-[#111] hover:text-[#111] transition-all">
                  Clear dates
                </button>
              )}
            </div>
            {dateFilterLabel() && (
              <p className="text-[10px] text-[#999] font-mono mt-1.5">Showing: {dateFilterLabel()}</p>
            )}
          </div>

          {/* Filters */}
          <div className="flex flex-wrap gap-2 mb-6">
            <select value={sector} onChange={e => setParam('sector', e.target.value)}
              className="px-3 py-1.5 text-xs font-medium uppercase tracking-[0.06em] border border-[#e0e0e0] bg-white text-[#666] focus:border-[#111] cursor-pointer">
              <option value="">All Sectors</option>
              {SECTORS.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
            <select value={type} onChange={e => setParam('type', e.target.value)}
              className="px-3 py-1.5 text-xs font-medium uppercase tracking-[0.06em] border border-[#e0e0e0] bg-white text-[#666] focus:border-[#111] cursor-pointer">
              <option value="">All Types</option>
              {TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
            <select value={minImportance} onChange={e => setParam('min_importance', e.target.value)}
              className="px-3 py-1.5 text-xs font-medium uppercase tracking-[0.06em] border border-[#e0e0e0] bg-white text-[#666] focus:border-[#111] cursor-pointer">
              {IMPORTANCE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
            {hasFilters && (
              <button onClick={clearFilters}
                className="px-3 py-1.5 text-xs font-medium uppercase tracking-[0.06em] border border-[#e0e0e0] text-[#999] hover:border-[#111] hover:text-[#111] transition-all">
                Clear all
              </button>
            )}
          </div>

          {error && (
            <div className="border border-[#111] p-4 mb-6 bg-[#fafafa]">
              <p className="label mb-1">Connection Error</p>
              <p className="text-xs font-light text-[#444]">Cannot reach backend on port 8000. Is uvicorn running?</p>
            </div>
          )}

          {loading ? (
            <div className="space-y-px"><Skeleton /><Skeleton /><Skeleton /></div>
          ) : events.length === 0 ? (
            <div className="py-16 flex flex-col items-center gap-6">
              <FlowEmpty size={120} />
              <div className="text-center">
                <p className="label mb-1">No events</p>
                <p className="text-xs font-light text-[#999]">
                  {hasFilters ? 'No events match the current filters.' : 'Fetch fresh data from the top-right.'}
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-px">
              {events.map(ev => (
                <EventCard key={ev.id} event={ev}
                  onTagClick={handleTagClick} activeTag={activeTag}
                  selected={selectedEvent?.id === ev.id}
                  onSelect={ev => setSelectedEvent(prev => prev?.id === ev.id ? null : ev)}
                  compact={!!selectedEvent}
                />
              ))}
            </div>
          )}

          <LoadMore hasMore={hasMore} loading={loadingMore} onLoadMore={handleLoadMore} />
        </div>
      </div>

      {selectedEvent && (
        <div className="flex-1 overflow-hidden">
          <AnalysisPanel event={selectedEvent} onClose={() => setSelectedEvent(null)} />
        </div>
      )}
    </div>
  )
}

// ── Intelligence feed ─────────────────────────────────────────────────────────
function IntelligenceFeed({ counts }) {
  const [events, setEvents]           = useState([])
  const [page, setPage]               = useState(1)
  const [total, setTotal]             = useState(0)
  const [hasMore, setHasMore]         = useState(false)
  const [loading, setLoading]         = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [intelType, setIntelType]     = useState('')
  const [sort, setSort]               = useState('recent')

  const fetchPage = useCallback(async (pg, replace = false) => {
    try {
      const params = { page: pg, limit: 20, sort }
      if (intelType) params.intel_type = intelType
      const data = await api.getIntelFeed(params)
      setEvents(prev => replace ? data.events : [...prev, ...data.events])
      setTotal(data.total); setHasMore(data.has_more); setPage(pg)
    } catch (e) { console.error('[IntelFeed]', e) }
  }, [intelType, sort])

  useEffect(() => {
    setLoading(true); setEvents([])
    fetchPage(1, true).finally(() => setLoading(false))
  }, [fetchPage])

  const handleLoadMore = useCallback(async () => {
    if (loadingMore || !hasMore) return
    setLoadingMore(true)
    await fetchPage(page + 1)
    setLoadingMore(false)
  }, [loadingMore, hasMore, page, fetchPage])

  return (
    <div className="w-full max-w-3xl mx-auto overflow-y-auto">
      <div className="px-6 py-6">

        {/* Controls */}
        <div className="flex items-center justify-between mb-4">
          <p className="text-xs text-[#999]">{total.toLocaleString()} intelligence events</p>
          <div className="flex gap-1 border border-[#e0e0e0] text-[10px] font-medium uppercase tracking-[0.06em]">
            {[['recent','Recent'],['top','Top']].map(([key, label]) => (
              <button key={key} onClick={() => { setSort(key); setPage(1); setEvents([]) }}
                className={`px-3 py-1.5 transition-colors ${sort === key ? 'bg-[#111] text-white' : 'text-[#999] hover:text-[#111]'}`}>
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Type filter tabs */}
        <div className="flex flex-wrap gap-1 mb-5">
          {INTEL_TYPES.map(({ value, label }) => {
            const count = value === '' ? counts?.total : counts?.[value]
            return (
              <button key={value}
                onClick={() => { setIntelType(value); setPage(1); setEvents([]) }}
                className={`px-3 py-1.5 text-[10px] font-medium uppercase tracking-[0.06em] border transition-all ${
                  intelType === value
                    ? 'bg-[#111] text-white border-[#111]'
                    : 'border-[#e0e0e0] text-[#666] hover:border-[#999] hover:text-[#111]'
                }`}>
                {label}
                {count != null && (
                  <span className={`ml-1.5 font-mono ${intelType === value ? 'text-[#ccc]' : 'text-[#bbb]'}`}>
                    {count > 9999 ? '9999+' : count}
                  </span>
                )}
              </button>
            )
          })}
        </div>

        {loading ? (
          <div className="space-y-px">
            {[...Array(5)].map((_, i) => <IntelSkeleton key={i} />)}
          </div>
        ) : events.length === 0 ? (
          <div className="py-16 flex flex-col items-center gap-6">
            <FlowEmpty size={120} />
            <div className="text-center">
              <p className="label mb-1">No intel events</p>
              <p className="text-xs font-light text-[#999]">
                Run ingestion from the Financial tab to populate intelligence streams.
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-px">
            {events.map(ev => <IntelCard key={ev.id} event={ev} />)}
          </div>
        )}

        <LoadMore hasMore={hasMore} loading={loadingMore} onLoadMore={handleLoadMore} />
      </div>
    </div>
  )
}

// ── Root Feed page ────────────────────────────────────────────────────────────
export default function Feed() {
  const [feedTab, setFeedTab]   = useState('financial')  // 'financial' | 'intelligence'
  const [health, setHealth]     = useState(null)
  const [enriching, setEnriching] = useState(false)
  const [ingesting, setIngesting] = useState(false)
  const [intelCounts, setIntelCounts] = useState(null)

  const fetchHealth = useCallback(() =>
    api.health().then(setHealth).catch(() => {}), [])

  useEffect(() => {
    fetchHealth()
    api.getIntelCounts().then(setIntelCounts).catch(() => {})
    const id = setInterval(fetchHealth, 20000)
    return () => clearInterval(id)
  }, [fetchHealth])

  async function handleEnrich() {
    setEnriching(true)
    await api.adminEnrich().catch(() => {})
    let polls = 0
    const iv = setInterval(async () => {
      await fetchHealth(); polls++
      if (polls >= 12) { clearInterval(iv); setEnriching(false) }
    }, 5000)
  }

  async function handleIngest() {
    setIngesting(true)
    await api.adminIngest().catch(() => {})
    setTimeout(async () => {
      await fetchHealth()
      api.getIntelCounts().then(setIntelCounts).catch(() => {})
      setIngesting(false)
    }, 8000)
  }

  const pending = health?.pending ?? 0

  return (
    <div className="flex flex-col h-full overflow-hidden">

      {/* Page header */}
      <div className="border-b border-[#e0e0e0] px-6 pt-6 pb-0 flex-shrink-0">
        <div className="flex items-end justify-between mb-4">
          <div>
            <p className="label text-[#999] mb-1">Capital Lens</p>
            <h1 className="text-2xl font-bold tracking-tight text-[#111]">Intelligence Feed</h1>
          </div>
        </div>

        {/* Primary tabs: Financial | Intelligence */}
        <div className="flex">
          {[
            { key: 'financial',     label: 'Financial',     count: health?.events },
            { key: 'intelligence',  label: 'Intelligence',  count: intelCounts?.total },
          ].map(({ key, label, count }) => (
            <button key={key} onClick={() => setFeedTab(key)}
              className={`px-5 py-3 text-xs font-medium uppercase tracking-[0.08em] border-b-2 -mb-px transition-colors ${
                feedTab === key ? 'border-[#111] text-[#111]' : 'border-transparent text-[#999] hover:text-[#555]'
              }`}>
              {label}
              {count != null && (
                <span className="ml-1.5 font-mono text-[10px] text-[#bbb]">
                  {count.toLocaleString()}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-hidden">
        {feedTab === 'financial' ? (
          <FinancialFeed
            health={health}
            onEnrich={handleEnrich}
            onIngest={handleIngest}
            enriching={enriching}
            ingesting={ingesting}
          />
        ) : (
          <IntelligenceFeed counts={intelCounts} />
        )}
      </div>
    </div>
  )
}
