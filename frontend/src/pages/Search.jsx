import { useState, useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import EventCard from '../components/EventCard'
import EntityAvatar from '../components/EntityAvatar'
import { NetworkEmpty } from '../components/Illustrations'
import { api } from '../lib/api'
import { formatAmount } from '../lib/format'

export default function Search() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [query, setQuery] = useState(searchParams.get('q') || '')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const inputRef = useRef(null)

  // Auto-focus on mount
  useEffect(() => { inputRef.current?.focus() }, [])

  // Run search when URL has ?q=
  useEffect(() => {
    const q = searchParams.get('q')
    if (q && q.length >= 2) {
      setQuery(q)
      doSearch(q)
    }
  }, [])

  async function doSearch(q) {
    if (!q || q.length < 2) return
    setLoading(true)
    setError(null)
    try {
      const data = await api.search(q)
      setResults(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  function handleSubmit(e) {
    e.preventDefault()
    if (query.trim().length < 2) return
    setSearchParams({ q: query.trim() })
    doSearch(query.trim())
  }

  const totalResults = results ? (results.entities?.length || 0) + (results.events?.length || 0) : 0

  return (
    <div className="max-w-3xl mx-auto px-6 py-10">

      {/* Header */}
      <div className="pb-6 mb-8 border-b border-[#e0e0e0]">
        <p className="label text-[#999] mb-1">Directory</p>
        <h1 className="text-2xl font-bold tracking-tight text-[#111]">Search</h1>
      </div>

      {/* Search bar */}
      <form onSubmit={handleSubmit} className="flex gap-0 mb-8 border border-[#e0e0e0] focus-within:border-[#111] transition-colors duration-200">
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Search events, entities, headlines…"
          className="flex-1 bg-white px-4 py-3 text-sm text-[#111] focus:outline-none placeholder-[#bbb] font-light"
        />
        <button
          type="submit"
          disabled={loading || query.length < 2}
          className="px-5 py-3 bg-[#111] text-white text-[10px] font-medium uppercase tracking-[0.08em] hover:bg-[#000] disabled:opacity-30 transition-colors duration-200 flex-shrink-0 border-l border-[#111]"
        >
          {loading ? (
            <span className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin inline-block" />
          ) : 'Search'}
        </button>
      </form>

      {/* Error */}
      {error && (
        <div className="border border-[#111] p-4 mb-6">
          <p className="label mb-1">Error</p>
          <p className="text-xs font-light text-[#444]">{error}</p>
        </div>
      )}

      {/* Results */}
      {results && (
        <>
          {/* Summary line */}
          <div className="flex items-center gap-4 mb-6">
            <p className="label text-[#999]">
              {totalResults === 0 ? 'No results' : `${totalResults} result${totalResults !== 1 ? 's' : ''}`} for "{results.query}"
            </p>
            <div className="flex-1 h-px bg-[#e0e0e0]" />
          </div>

          {/* Entities section */}
          {results.entities?.length > 0 && (
            <div className="mb-8">
              <div className="flex items-center gap-4 mb-4">
                <p className="label text-[#999]">Entities</p>
                <div className="flex-1 h-px bg-[#e0e0e0]" />
                <p className="label text-[#ccc]">{results.entities.length}</p>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-px bg-[#e0e0e0]">
                {results.entities.map(en => (
                  <button
                    key={en.id}
                    onClick={() => navigate(`/entities/${en.id}`)}
                    className="bg-white p-4 text-left hover:bg-[#fafafa] transition-colors duration-200 group"
                  >
                    <div className="flex items-center gap-3">
                      <EntityAvatar name={en.name} size="md" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-bold text-[#111] truncate group-hover:underline">{en.name}</p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-[10px] font-medium uppercase tracking-[0.06em] text-[#999]">{en.sector}</span>
                          {en.net_worth && (
                            <span className="text-[10px] font-mono font-bold text-[#666]">
                              {formatAmount(en.net_worth).replace(' USD', '')}
                            </span>
                          )}
                        </div>
                      </div>
                      <span className="text-[#ccc] group-hover:text-[#111] transition-colors text-xs">→</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Events section */}
          {results.events?.length > 0 && (
            <div>
              <div className="flex items-center gap-4 mb-4">
                <p className="label text-[#999]">Events</p>
                <div className="flex-1 h-px bg-[#e0e0e0]" />
                <p className="label text-[#ccc]">{results.events.length}</p>
              </div>
              <div className="space-y-px">
                {results.events.map(ev => (
                  <EventCard key={ev.id} event={ev} />
                ))}
              </div>
            </div>
          )}

          {/* No results */}
          {totalResults === 0 && (
            <div className="py-16 flex flex-col items-center gap-6">
              <NetworkEmpty size={120} />
              <div className="text-center">
                <p className="label mb-1">No results</p>
                <p className="text-xs font-light text-[#999]">
                  Try a different query — company names, keywords, or event types work best.
                </p>
              </div>
            </div>
          )}
        </>
      )}

      {/* Empty state (no search yet) */}
      {!results && !loading && (
        <div className="py-16 flex flex-col items-center gap-6">
          <NetworkEmpty size={120} />
          <div className="text-center">
            <p className="label mb-1">Search the database</p>
            <p className="text-xs font-light text-[#999]">
              Try "Apple", "acquisition", "Elon Musk", or "SEC Filing"
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
