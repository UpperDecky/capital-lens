import { useState, useEffect, useCallback } from 'react'

function MetricCard({ label, value, sub }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
      <div className="text-gray-400 text-xs uppercase tracking-wider mb-1">{label}</div>
      <div className="text-2xl font-bold text-white">{value ?? '--'}</div>
      {sub && <div className="text-gray-500 text-xs mt-1">{sub}</div>}
    </div>
  )
}

function FunnelBar({ label, count, max }) {
  const pct = max > 0 ? Math.round((count / max) * 100) : 0
  return (
    <div className="flex items-center gap-3 py-1.5">
      <div className="w-28 text-sm text-gray-400 text-right">{label}</div>
      <div className="flex-1 bg-gray-800 rounded-full h-4 overflow-hidden">
        <div
          className="bg-blue-500 h-4 rounded-full transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="w-10 text-sm text-gray-300 text-right">{count}</div>
    </div>
  )
}

export default function AdminAnalytics() {
  const [weekly, setWeekly] = useState(null)
  const [dau, setDau] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [secret, setSecret] = useState(() => localStorage.getItem('adminSecret') || '')

  const load = useCallback(async () => {
    if (!secret) return
    setLoading(true)
    setError(null)
    try {
      const headers = { 'X-Admin-Secret': secret }
      const [wRes, dRes] = await Promise.all([
        fetch('/admin/analytics/weekly', { headers }),
        fetch('/admin/analytics/dau?days=14', { headers }),
      ])
      if (!wRes.ok) throw new Error(`Weekly: ${wRes.status}`)
      if (!dRes.ok) throw new Error(`DAU: ${dRes.status}`)
      setWeekly(await wRes.json())
      setDau(await dRes.json())
      localStorage.setItem('adminSecret', secret)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [secret])

  useEffect(() => { load() }, [load])

  const funnel = weekly?.funnel || {}
  const funnelMax = funnel.signups || 1

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Analytics</h1>
        <div className="flex gap-2">
          <input
            type="password"
            placeholder="Admin secret"
            value={secret}
            onChange={e => setSecret(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-200 w-40"
          />
          <button
            onClick={load}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-1.5 rounded text-sm"
          >
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-900/40 border border-red-700 text-red-300 rounded p-3 mb-4 text-sm">
          {error}
        </div>
      )}

      {weekly && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <MetricCard label="Total Events (7d)" value={weekly.summary?.total_events} />
            <MetricCard label="Signups" value={weekly.summary?.signups} />
            <MetricCard label="Logins" value={weekly.summary?.logins} />
            <MetricCard label="Searches" value={weekly.summary?.searches} />
          </div>

          <div className="grid md:grid-cols-2 gap-6 mb-6">
            <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
              <h2 className="text-sm font-semibold text-gray-300 mb-4 uppercase tracking-wider">
                Conversion Funnel
              </h2>
              {Object.entries(funnel).map(([key, count]) => (
                <FunnelBar key={key} label={key} count={count} max={funnelMax} />
              ))}
            </div>

            <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
              <h2 className="text-sm font-semibold text-gray-300 mb-4 uppercase tracking-wider">
                Top Features
              </h2>
              <div className="space-y-2">
                {(weekly.top_features || []).slice(0, 8).map(({ feature, count }) => (
                  <div key={feature} className="flex justify-between text-sm">
                    <span className="text-gray-300 font-mono">{feature}</span>
                    <span className="text-gray-500">{count}</span>
                  </div>
                ))}
                {(!weekly.top_features || weekly.top_features.length === 0) && (
                  <div className="text-gray-600 text-sm">No feature usage data yet</div>
                )}
              </div>
            </div>
          </div>
        </>
      )}

      {dau && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <h2 className="text-sm font-semibold text-gray-300 mb-4 uppercase tracking-wider">
            Daily Active Users (14d)
          </h2>
          <div className="flex items-end gap-1 h-24">
            {dau.data.map(({ date, dau: count }) => {
              const max = Math.max(...dau.data.map(d => d.dau), 1)
              const h = Math.round((count / max) * 96)
              return (
                <div key={date} className="flex flex-col items-center flex-1 gap-1 group">
                  <div className="relative">
                    <div
                      className="bg-blue-500 rounded-t w-full min-w-[6px] group-hover:bg-blue-400 transition-colors"
                      style={{ height: `${h}px` }}
                      title={`${date}: ${count}`}
                    />
                  </div>
                  <div className="text-gray-600 text-xs" style={{ fontSize: '9px' }}>
                    {date.slice(5)}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {loading && !weekly && (
        <div className="text-gray-500 text-center py-12">Loading...</div>
      )}
    </div>
  )
}
