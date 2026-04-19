export default function ImplicationRow({ marketImpact, investSignal }) {
  if (!marketImpact && !investSignal) return null
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-0 border border-[#e0e0e0] mt-3">
      {marketImpact && (
        <div className={`p-4 ${investSignal ? 'border-r border-[#e0e0e0]' : ''}`}>
          <p className="label mb-2">Market Impact</p>
          <p className="text-xs font-light text-[#333] leading-relaxed">{marketImpact}</p>
        </div>
      )}
      {investSignal && (
        <div className="p-4">
          <p className="label mb-2">Investment Signal</p>
          <p className="text-xs font-light text-[#333] leading-relaxed">{investSignal}</p>
        </div>
      )}
    </div>
  )
}
