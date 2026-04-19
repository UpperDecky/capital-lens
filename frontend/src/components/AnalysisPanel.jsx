/**
 * AnalysisPanel — right-side deep analysis panel for a selected event.
 * Shows relationships, affected sectors, timeline projections, and context.
 * All data comes from pre-computed enrichment stored in event.analysis.
 */
import EntityAvatar from './EntityAvatar'
import { formatAmount, formatDate, timeAgo, eventTypeLabel } from '../lib/format'
import { useNavigate } from 'react-router-dom'

/** Impact indicator bar — a row of filled squares */
function ImpactBar({ impact }) {
  const map = {
    positive: { fill: 3, label: '▲ Positive' },
    negative: { fill: 3, label: '▼ Negative' },
    neutral:  { fill: 1, label: '— Neutral'  },
  }
  const { fill, label } = map[impact] || map.neutral
  return (
    <span className="flex items-center gap-1">
      {[0,1,2].map(i => (
        <span
          key={i}
          className={`inline-block w-1.5 h-1.5 ${
            i < fill
              ? impact === 'positive' ? 'bg-[#111]' : impact === 'negative' ? 'bg-[#111]' : 'bg-[#bbb]'
              : 'bg-[#e0e0e0]'
          }`}
        />
      ))}
      <span className="text-[9px] font-medium uppercase tracking-[0.07em] text-[#666] ml-0.5">{label}</span>
    </span>
  )
}

/** Direction badge for entity relationships */
function DirectionTag({ direction }) {
  const labels = {
    supplier:    'Supplier',
    customer:    'Customer',
    competitor:  'Competitor',
    partner:     'Partner',
    investor:    'Investor',
    subsidiary:  'Subsidiary',
  }
  return (
    <span className="text-[9px] font-medium uppercase tracking-[0.08em] border border-[#e0e0e0] px-1.5 py-0.5 text-[#999]">
      {labels[direction] || direction}
    </span>
  )
}

/** Likelihood dot */
function Likelihood({ level }) {
  const map = { high: '#111', medium: '#888', low: '#ccc' }
  return (
    <span className="flex items-center gap-1">
      <span className="w-1.5 h-1.5 rounded-full inline-block" style={{ background: map[level] || '#ccc' }} />
      <span className="text-[9px] uppercase tracking-[0.06em] text-[#999] font-medium">{level}</span>
    </span>
  )
}

/** Timeframe label */
function TimeframeLabel({ timeframe }) {
  const map = {
    immediate:    'Now',
    short_term:   'Short',
    medium_term:  'Medium',
    long_term:    'Long',
  }
  return (
    <span className="text-[9px] font-medium uppercase tracking-[0.06em] border border-[#e0e0e0] px-1.5 py-0.5 text-[#999]">
      {map[timeframe] || timeframe}
    </span>
  )
}

/** Section wrapper */
function Section({ label, children }) {
  return (
    <div className="border-b border-[#e0e0e0]">
      <div className="px-4 pt-3 pb-1">
        <p className="label text-[#999]">{label}</p>
      </div>
      <div className="pb-3">{children}</div>
    </div>
  )
}

export default function AnalysisPanel({ event, onClose }) {
  const navigate = useNavigate()
  if (!event) return null

  const analysis = event.analysis || null
  const hasAnalysis = analysis && (
    analysis.relationships?.length ||
    analysis.affected_sectors?.length ||
    analysis.timeline?.length ||
    analysis.context
  )

  return (
    <aside className="flex flex-col bg-white border-l border-[#e0e0e0] h-full overflow-hidden animate-slide-in">

      {/* Panel header */}
      <div className="flex items-stretch border-b border-[#e0e0e0] flex-shrink-0">
        <button
          onClick={() => navigate(`/entities/${event.entity_id}`)}
          className="p-4 border-r border-[#e0e0e0] hover:bg-[#f5f5f5] transition-colors duration-200 flex-shrink-0"
        >
          <EntityAvatar name={event.entity_name} size="sm" />
        </button>
        <div className="flex-1 px-4 py-3 min-w-0">
          <button
            onClick={() => navigate(`/entities/${event.entity_id}`)}
            className="text-xs font-bold text-[#111] hover:underline tracking-tight truncate block"
          >
            {event.entity_name}
          </button>
          <div className="flex items-center gap-2 mt-0.5 flex-wrap">
            <span className="label text-[#999]">{event.entity_sector}</span>
            <span className="label border border-[#e0e0e0] px-1.5 py-px text-[#666]">
              {eventTypeLabel(event.event_type)}
            </span>
          </div>
        </div>
        <button
          onClick={onClose}
          className="px-4 text-[#bbb] hover:text-[#111] border-l border-[#e0e0e0] hover:bg-[#f5f5f5] transition-all duration-200 text-sm flex-shrink-0"
          title="Close panel"
        >
          ✕
        </button>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto">

        {/* Headline + meta */}
        <div className="px-4 py-3 border-b border-[#e0e0e0]">
          <p className="text-xs font-medium text-[#111] leading-snug">{event.headline}</p>
          <div className="flex items-center gap-3 mt-1.5 flex-wrap">
            {event.amount && (
              <span className="font-mono text-[10px] font-bold text-[#111]">
                {formatAmount(event.amount, event.currency)}
              </span>
            )}
            <span className="text-[10px] text-[#999] font-light">
              {formatDate(event.occurred_at)}
            </span>
            {event.enriched_at && (
              <span className="text-[10px] text-[#ccc] font-light">
                · enriched {timeAgo(event.enriched_at)}
              </span>
            )}
          </div>
        </div>

        {/* Plain English */}
        {event.plain_english && (
          <Section label="Summary">
            <div className="flex">
              <div className="w-0.5 bg-[#111] flex-shrink-0 mx-4" />
              <p className="text-xs text-[#333] leading-relaxed font-light pr-4">{event.plain_english}</p>
            </div>
          </Section>
        )}

        {/* Context (deep analysis) */}
        {analysis?.context && (
          <Section label="Strategic Context">
            <p className="px-4 text-xs text-[#333] leading-relaxed font-light">{analysis.context}</p>
          </Section>
        )}

        {/* Entity Relationships */}
        {analysis?.relationships?.length > 0 && (
          <Section label="Entity Relationships">
            <div className="divide-y divide-[#f0f0f0]">
              {analysis.relationships.map((rel, i) => (
                <div key={i} className="px-4 py-2.5 flex items-start gap-3">
                  <EntityAvatar name={rel.entity} size="xs" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-0.5">
                      <span className="text-xs font-bold text-[#111] truncate">{rel.entity}</span>
                      <DirectionTag direction={rel.direction} />
                    </div>
                    <p className="text-[11px] text-[#666] leading-snug font-light">{rel.relationship}</p>
                  </div>
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Affected Sectors */}
        {analysis?.affected_sectors?.length > 0 && (
          <Section label="Sector Implications">
            <div className="divide-y divide-[#f0f0f0]">
              {analysis.affected_sectors.map((s, i) => (
                <div key={i} className="px-4 py-2.5">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-bold text-[#111]">{s.sector}</span>
                    <div className="flex items-center gap-2">
                      <TimeframeLabel timeframe={s.timeframe} />
                      <ImpactBar impact={s.impact} />
                    </div>
                  </div>
                  <p className="text-[11px] text-[#666] leading-snug font-light">{s.reason}</p>
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Timeline Projections */}
        {analysis?.timeline?.length > 0 && (
          <Section label="Projected Timeline">
            <div className="px-4 space-y-0 relative">
              {/* Vertical line */}
              <div className="absolute left-[1.35rem] top-2 bottom-2 w-px bg-[#e0e0e0]" />
              {analysis.timeline.map((t, i) => (
                <div key={i} className="flex items-start gap-3 py-2.5">
                  {/* Node dot */}
                  <div className={`w-2 h-2 flex-shrink-0 mt-1 border border-[#ccc] relative z-10 ${
                    i === 0 ? 'bg-[#111] border-[#111]' : 'bg-white'
                  }`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-[10px] font-medium uppercase tracking-[0.06em] text-[#999] border border-[#e0e0e0] px-1.5 py-px">
                        {t.period}
                      </span>
                      <Likelihood level={t.likelihood} />
                    </div>
                    <p className="text-[11px] text-[#444] leading-snug font-light">{t.event}</p>
                  </div>
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Market Impact + Investment Signal (always shown if available) */}
        {event.market_impact && (
          <Section label="Market Impact">
            <p className="px-4 text-xs text-[#333] leading-relaxed font-light">{event.market_impact}</p>
          </Section>
        )}

        {event.invest_signal && (
          <Section label="Investment Signal">
            <p className="px-4 text-xs text-[#333] leading-relaxed font-light">{event.invest_signal}</p>
          </Section>
        )}

        {event.for_you && (
          <Section label="Personal Takeaway">
            <div className="flex mx-4">
              <div className="w-0.5 bg-[#bbb] flex-shrink-0 mr-3" />
              <p className="text-xs text-[#444] leading-relaxed font-light">{event.for_you}</p>
            </div>
          </Section>
        )}

        {/* Pending state */}
        {!event.plain_english && (
          <div className="px-4 py-6 flex flex-col items-center gap-3">
            <div className="w-full h-px bg-[#f0f0f0] relative overflow-hidden">
              <div className="absolute inset-y-0 w-1/3 bg-gradient-to-r from-transparent via-[#ccc] to-transparent animate-scan" />
            </div>
            <p className="text-[10px] uppercase tracking-[0.1em] text-[#bbb] font-medium">
              AI analysis queued
            </p>
            <p className="text-[11px] text-[#ccc] font-light text-center">
              Deep analysis will appear here after enrichment runs.
            </p>
          </div>
        )}

        {/* No deep analysis yet */}
        {event.plain_english && !hasAnalysis && (
          <div className="px-4 py-4 border-b border-[#e0e0e0]">
            <p className="text-[10px] uppercase tracking-[0.08em] text-[#ccc] font-medium">
              Extended analysis not yet generated
            </p>
            <p className="text-[11px] text-[#ccc] font-light mt-1">
              Run the enrichment scheduler to generate relationships, sector implications, and timeline projections.
            </p>
          </div>
        )}

        {/* Source link */}
        {event.source_url && (
          <div className="px-4 py-3">
            <a
              href={event.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[10px] font-medium uppercase tracking-[0.08em] text-[#999] hover:text-[#111] transition-colors duration-200"
            >
              View original source ↗
            </a>
          </div>
        )}
      </div>
    </aside>
  )
}
