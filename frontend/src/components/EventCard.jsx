/**
 * EventCard — renders a single event in the feed.
 * Props:
 *   event      — the event object
 *   onTagClick — called with tag string when a tag pill is clicked
 *   activeTag  — currently active tag string for highlight
 *   selected   — boolean: is this card currently selected (panel open)?
 *   onSelect   — called with event when the card body is clicked
 *   compact    — boolean: panel is open, shrink the card slightly
 */
import { useNavigate } from 'react-router-dom'
import EntityAvatar from './EntityAvatar'
import ImplicationRow from './ImplicationRow'
import TagPill from './TagPill'
import { formatAmount, formatDateTime, eventTypeLabel, JARGON } from '../lib/format'

/** Inline jargon tooltip — underline with definition on hover */
function JargonText({ text }) {
  if (!text) return null
  const parts = []
  let last = 0
  const lower = text.toLowerCase()
  const sorted = Object.keys(JARGON).sort((a, b) => b.length - a.length)
  const matches = []
  for (const term of sorted) {
    let idx = lower.indexOf(term)
    while (idx !== -1) {
      matches.push({ idx, len: term.length, term })
      idx = lower.indexOf(term, idx + 1)
    }
  }
  matches.sort((a, b) => a.idx - b.idx)
  const filtered = matches.filter((m, i) =>
    i === 0 || m.idx >= matches[i - 1].idx + matches[i - 1].len
  )
  for (const { idx, len, term } of filtered) {
    if (idx > last) parts.push(<span key={`t-${last}`}>{text.slice(last, idx)}</span>)
    parts.push(
      <span key={`j-${idx}`} className="relative group cursor-help"
        style={{ borderBottom: '1px dotted #999' }}>
        {text.slice(idx, idx + len)}
        <span className="absolute bottom-full left-0 mb-2 w-56 p-2.5 bg-[#111] text-[#eee] text-[10px] leading-relaxed font-light opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity duration-200 z-50"
          style={{ border: '1px solid #333' }}>
          <strong className="block text-white font-medium mb-1 uppercase tracking-[0.06em] text-[9px]">
            {term}
          </strong>
          {JARGON[term]}
        </span>
      </span>
    )
    last = idx + len
  }
  if (last < text.length) parts.push(<span key="t-end">{text.slice(last)}</span>)
  return <>{parts}</>
}

/** Importance score indicator — 1–5 filled squares */
function ImportanceBadge({ score }) {
  if (!score) return null
  const LABELS = { 1: 'Minimal', 2: 'Low', 3: 'Notable', 4: 'High', 5: 'Critical' }
  return (
    <span
      className="flex items-center gap-0.5 flex-shrink-0"
      title={`Priority ${score}/5 — ${LABELS[score] || ''}`}
    >
      {[1, 2, 3, 4, 5].map(i => (
        <span
          key={i}
          className={`inline-block w-1.5 h-1.5 ${
            i <= score
              ? score === 5 ? 'bg-[#111]'
              : score === 4 ? 'bg-[#333]'
              : score === 3 ? 'bg-[#666]'
              : 'bg-[#999]'
              : 'bg-[#e0e0e0]'
          }`}
        />
      ))}
    </span>
  )
}

export default function EventCard({ event, onTagClick, activeTag, selected, onSelect, compact }) {
  const navigate = useNavigate()
  const hasEnrichment = event.plain_english || event.market_impact || event.invest_signal || event.for_you

  return (
    <article
      className={`bg-white border transition-all duration-200 animate-fade-in cursor-pointer ${
        selected
          ? 'border-[#111] border-l-2'
          : 'border-[#e0e0e0] hover:border-[#111]'
      }`}
      onClick={() => onSelect?.(event)}
    >
      {/* Selected indicator — top accent line */}
      {selected && <div className="h-px bg-[#111]" />}

      {/* Header strip */}
      <div className="flex items-stretch border-b border-[#e0e0e0]">
        {/* Avatar block */}
        <button
          onClick={e => { e.stopPropagation(); navigate(`/entities/${event.entity_id}`) }}
          className="p-4 border-r border-[#e0e0e0] hover:bg-[#f5f5f5] transition-colors duration-200 flex-shrink-0"
        >
          <EntityAvatar name={event.entity_name} size="md" />
        </button>

        {/* Meta */}
        <div className="flex-1 px-4 py-3 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <button
              onClick={e => { e.stopPropagation(); navigate(`/entities/${event.entity_id}`) }}
              className="text-sm font-bold text-[#111] hover:underline tracking-tight"
            >
              {event.entity_name}
            </button>
            <span className="label text-[#999]">{event.entity_sector}</span>
            <span className="label border border-[#e0e0e0] px-1.5 py-px text-[#666]">
              {event.event_type === 'congressional_trade' ? 'Congress' : eventTypeLabel(event.event_type)}
            </span>
            {event.amount && (
              <span className="font-mono text-xs font-bold text-[#111]">
                {formatAmount(event.amount, event.currency)}
              </span>
            )}
            <ImportanceBadge score={event.importance} />
          </div>
          <p className="text-[10px] text-[#999] mt-0.5 font-light flex items-center gap-1.5 flex-wrap">
            {event.source_name && <span>{event.source_name}</span>}
            {(event.occurred_at || event.ingested_at) && (
              <><span className="text-[#ddd]">·</span>
              <span>{formatDateTime(event.occurred_at || event.ingested_at)}</span></>
            )}
          </p>
        </div>

        {/* Source link */}
        {event.source_url && (
          <a href={event.source_url} target="_blank" rel="noopener noreferrer"
            onClick={e => e.stopPropagation()}
            className="px-4 flex items-center border-l border-[#e0e0e0] text-[#ccc] hover:text-[#111] hover:bg-[#f5f5f5] transition-all duration-200 text-xs flex-shrink-0"
            title="View source">
            ↗
          </a>
        )}
      </div>

      {/* Headline */}
      <div className="px-4 py-3 border-b border-[#e0e0e0]">
        <p className="text-sm font-medium text-[#111] leading-snug">{event.headline}</p>
      </div>

      {/* Enrichment — hide detail rows in compact mode if panel is open */}
      {hasEnrichment ? (
        <div>
          {/* Plain English */}
          {event.plain_english && (
            <div className="flex border-b border-[#e0e0e0]">
              <div className="w-1 bg-[#111] flex-shrink-0" />
              <div className="flex-1 px-4 py-3">
                <p className="label mb-1.5">Plain English</p>
                <p className="text-xs text-[#333] leading-relaxed font-light">
                  <JargonText text={event.plain_english} />
                </p>
              </div>
            </div>
          )}

          {/* Market Impact + Investment Signal — hidden in compact mode */}
          {!compact && (event.market_impact || event.invest_signal) && (
            <div className="border-b border-[#e0e0e0]">
              <ImplicationRow
                marketImpact={event.market_impact}
                investSignal={event.invest_signal}
              />
            </div>
          )}

          {/* For You — hidden in compact mode */}
          {!compact && event.for_you && (
            <div className="flex border-b border-[#e0e0e0] bg-[#fafafa]">
              <div className="w-1 bg-[#e0e0e0] flex-shrink-0" />
              <div className="flex-1 px-4 py-3">
                <p className="label mb-1.5">For You</p>
                <p className="text-xs text-[#444] leading-relaxed font-light">{event.for_you}</p>
              </div>
            </div>
          )}

          {/* Compact mode hint */}
          {compact && selected && (
            <div className="px-4 py-2 flex items-center gap-2 border-b border-[#e0e0e0]">
              <div className="w-1.5 h-1.5 bg-[#111]" />
              <p className="text-[9px] uppercase tracking-[0.1em] text-[#999] font-medium">
                Analysis open →
              </p>
            </div>
          )}
        </div>
      ) : (
        <div className="px-4 py-3 border-b border-[#e0e0e0] flex items-center gap-3">
          <div className="flex-1 h-px bg-[#f0f0f0] relative overflow-hidden">
            <div className="absolute inset-y-0 w-1/3 bg-gradient-to-r from-transparent via-[#ccc] to-transparent animate-scan" />
          </div>
          <p className="text-[10px] uppercase tracking-[0.1em] text-[#bbb] font-medium flex-shrink-0">
            AI analysis queued
          </p>
          <div className="flex-1 h-px bg-[#f0f0f0] relative overflow-hidden">
            <div className="absolute inset-y-0 w-1/3 bg-gradient-to-r from-transparent via-[#ccc] to-transparent animate-scan" style={{ animationDelay: '0.7s' }} />
          </div>
        </div>
      )}

      {/* Tags */}
      {event.sector_tags?.length > 0 && (
        <div className="px-4 py-2.5 flex flex-wrap gap-1.5">
          {event.sector_tags.map(tag => (
            <TagPill
              key={tag}
              tag={tag}
              active={activeTag === tag}
              onClick={e => { e.stopPropagation(); onTagClick?.(tag) }}
            />
          ))}
        </div>
      )}
    </article>
  )
}
