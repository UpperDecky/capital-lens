import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { LedgerEmpty } from '../components/Illustrations'
import { api } from '../lib/api'
import { formatAmount } from '../lib/format'

function ThemeSkeleton() {
  return (
    <div className="bg-white border border-[#e0e0e0] animate-pulse">
      <div className="p-5 border-b border-[#e0e0e0] flex items-center gap-4">
        <div className="w-8 h-8 bg-[#f0f0f0]" />
        <div className="flex-1 space-y-2">
          <div className="h-3 w-32 bg-[#f0f0f0]" />
          <div className="h-2 w-20 bg-[#f5f5f5]" />
        </div>
      </div>
      <div className="p-5 space-y-2">
        <div className="h-2 w-full bg-[#f5f5f5]" />
        <div className="h-2 w-5/6 bg-[#f5f5f5]" />
      </div>
    </div>
  )
}

export default function Themes() {
  const navigate = useNavigate()
  const [themes, setThemes] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getThemes()
      .then(setThemes)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="max-w-4xl mx-auto px-6 py-10">

      {/* Header */}
      <div className="pb-6 mb-8 border-b border-[#e0e0e0]">
        <p className="label text-[#999] mb-1">Intelligence</p>
        <h1 className="text-2xl font-bold tracking-tight text-[#111]">Market Themes</h1>
        <p className="text-xs text-[#999] font-light mt-1">Aggregated signals by sector from enriched events</p>
      </div>

      {loading ? (
        <div className="space-y-px">
          <ThemeSkeleton /><ThemeSkeleton /><ThemeSkeleton />
        </div>
      ) : themes.length === 0 ? (
        <div className="py-20 flex flex-col items-center gap-6">
          <LedgerEmpty size={140} />
          <div className="text-center">
            <p className="label mb-1">No themes yet</p>
            <p className="text-xs font-light text-[#999]">
              Events need to be enriched before themes appear.
            </p>
          </div>
        </div>
      ) : (
        <div className="space-y-px">
          {themes.map((theme, i) => (
            <ThemeCard
              key={theme.theme}
              theme={theme}
              rank={i + 1}
              onViewFeed={() => navigate(`/?sector=${theme.theme}`)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function ThemeCard({ theme, rank, onViewFeed }) {
  return (
    <div className="bg-white border border-[#e0e0e0] hover:border-[#111] transition-all duration-200">

      {/* Header row */}
      <div className="flex items-stretch border-b border-[#e0e0e0]">
        {/* Rank block */}
        <div className="px-5 flex items-center justify-center border-r border-[#e0e0e0] min-w-[52px]">
          <span className="font-mono text-sm font-bold text-[#bbb]">
            {String(rank).padStart(2, '0')}
          </span>
        </div>

        {/* Title + stats */}
        <div className="flex-1 px-5 py-4">
          <h2 className="text-base font-bold tracking-tight text-[#111]">{theme.theme}</h2>
          <p className="text-[10px] font-medium uppercase tracking-[0.06em] text-[#999] mt-0.5">
            {theme.event_count} event{theme.event_count !== 1 ? 's' : ''}
            {theme.total_capital > 0 && (
              <span className="ml-2 font-mono text-[#666]">{formatAmount(theme.total_capital).replace(' USD', '')} moved</span>
            )}
          </p>
        </div>

        {/* View feed button */}
        <button
          onClick={onViewFeed}
          className="px-5 text-[10px] font-medium uppercase tracking-[0.06em] text-[#999] hover:text-[#111] hover:bg-[#f5f5f5] border-l border-[#e0e0e0] transition-colors duration-200 flex-shrink-0 flex items-center gap-1"
        >
          Feed ↗
        </button>
      </div>

      {/* Tags */}
      {theme.top_tags?.length > 0 && (
        <div className="px-5 py-3 flex flex-wrap gap-1.5 border-b border-[#e0e0e0]">
          {theme.top_tags.map(tag => (
            <span
              key={tag}
              className="px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.06em] border border-[#e0e0e0] text-[#666]"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Latest investment signal */}
      {theme.latest_signal && (
        <div className="flex">
          <div className="w-1 bg-[#111] flex-shrink-0" />
          <div className="flex-1 px-4 py-3">
            <p className="label text-[#999] mb-1.5">Latest Signal</p>
            <p className="text-xs text-[#333] leading-relaxed font-light">{theme.latest_signal}</p>
          </div>
        </div>
      )}
    </div>
  )
}
