export default function TierBadge({ tier, dailyRemaining, dailyLimit, resetAt }) {
  if (!tier || tier === 'anon') return null

  if (tier === 'pro') {
    return (
      <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-[#111] text-white text-[9px] font-semibold uppercase tracking-[0.1em] select-none">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 flex-shrink-0" />
        Pro
      </div>
    )
  }

  // free
  const limit = dailyLimit || 20
  const remaining = dailyRemaining ?? limit
  const used = limit - remaining
  const pct = Math.min(100, (used / limit) * 100)
  const isLow = remaining <= 5
  const isEmpty = remaining === 0

  return (
    <div className={`flex items-center gap-2 border px-2.5 py-1.5 select-none transition-colors ${
      isEmpty ? 'border-red-300 bg-red-50' : isLow ? 'border-amber-300 bg-amber-50' : 'border-[#e0e0e0] bg-white'
    }`}>
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <span className="text-[9px] font-semibold uppercase tracking-[0.1em] text-[#666]">Free</span>
          <span className={`text-[9px] font-mono tabular-nums ${
            isEmpty ? 'text-red-500 font-semibold' : isLow ? 'text-amber-600' : 'text-[#999]'
          }`}>
            {remaining}/{limit} today
          </span>
        </div>
        <div className="w-20 h-[3px] bg-[#f0f0f0] rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              isEmpty ? 'bg-red-400' : isLow ? 'bg-amber-400' : 'bg-[#111]'
            }`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    </div>
  )
}
