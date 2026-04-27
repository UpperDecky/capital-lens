import { useState, useEffect, useCallback } from 'react'

const STATUS_COLOR = {
  success: 'text-green-400',
  failed: 'text-red-400',
  stalled: 'text-yellow-400',
  never_run: 'text-gray-500',
}

const STATUS_DOT = {
  success: 'bg-green-400',
  failed: 'bg-red-400',
  stalled: 'bg-yellow-400',
  never_run: 'bg-gray-500',
}

function IngestorRow({ name, data }) {
  const color = STATUS_COLOR[data.status] || 'text-gray-400'
  const dot = STATUS_DOT[data.status] || 'bg-gray-500'
  return (
    <tr className="border-b border-gray-800 hover:bg-gray-800/40">
      <td className="py-2 px-3 font-mono text-sm text-gray-200">{name}</td>
      <td className="py-2 px-3">
        <span className="flex items-center gap-2">
          <span className={`inline-block w-2 h-2 rounded-full ${dot}`} />
          <span className={`text-sm font-medium ${color}`}>{data.status}</span>
        </span>
      </td>
      <td className="py-2 px-3 text-sm text-gray-400">
        {data.last_run_minutes_ago != null
          ? `${Math.round(data.last_run_minutes_ago)}m ago`
          : '--'}
      </td>
      <td className="py-2 px-3 text-sm text-gray-400">
        {data.consecutive_failures > 0 ? (
          <span className="text-red-400">{data.consecutive_failures} fail{data.consecutive_failures > 1 ? 's' : ''}</span>
        ) : '--'}
      </td>
      <td className="py-2 px-3 text-sm text-gray-400">
        {data.avg_duration_seconds != null
          ? `${data.avg_duration_seconds.toFixed(1)}s`
          : '--'}
      </td>
    </tr>
  )
}

export default function AdminDashboard() {
  const [health, setHealth] = useState(null)
  const [queue, setQueue] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [secret, setSecret] = useState(() => localStorage.getItem('adminSecret') || '')

  const load = useCallback(async () => {
    if (!secret) return
    setLoading(true)
    setError(null)
    try {
      const headers = { 'X-Admin-Secret': secret }
      const [hRes, qRes] = await Promise.all([
        fetch('/admin/health/ingestors', { headers }),
        fetch('/admin/health/queue', { headers }),
      ])
      if (!hRes.ok) throw new Error(`Health: ${hRes.status}`)
      if (!qRes.ok) throw new Error(`Queue: ${qRes.status}`)
      setHealth(await hRes.json())
      setQueue(await qRes.json())
      localStorage.setItem('adminSecret', secret)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [secret])

  useEffect(() => { load() }, [load])

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Data Health Dashboard</h1>
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

      {health && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          {[
            { label: 'Total', value: health.summary.total, color: 'text-gray-200' },
            { label: 'OK', value: health.summary.ok, color: 'text-green-400' },
            { label: 'Failed', value: health.summary.failed, color: 'text-red-400' },
            { label: 'Stalled', value: health.summary.stalled, color: 'text-yellow-400' },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-gray-900 border border-gray-800 rounded-lg p-4">
              <div className="text-gray-400 text-xs uppercase tracking-wider mb-1">{label}</div>
              <div className={`text-3xl font-bold ${color}`}>{value}</div>
            </div>
          ))}
        </div>
      )}

      {queue && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 mb-6">
          <h2 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wider">Enrichment Queue</h2>
          <div className="flex gap-8">
            <div>
              <div className="text-gray-400 text-xs">Pending</div>
              <div className={`text-2xl font-bold ${queue.status === 'critical' ? 'text-red-400' : queue.status === 'warning' ? 'text-yellow-400' : 'text-green-400'}`}>
                {queue.total_pending}
              </div>
            </div>
            <div>
              <div className="text-gray-400 text-xs">Oldest (hrs)</div>
              <div className="text-2xl font-bold text-gray-200">
                {queue.oldest_pending_age_hours ?? '--'}
              </div>
            </div>
            <div>
              <div className="text-gray-400 text-xs">Status</div>
              <div className={`text-lg font-semibold mt-1 ${queue.status === 'critical' ? 'text-red-400' : queue.status === 'warning' ? 'text-yellow-400' : 'text-green-400'}`}>
                {queue.status}
              </div>
            </div>
          </div>
        </div>
      )}

      {health && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
          <h2 className="text-sm font-semibold text-gray-300 p-4 uppercase tracking-wider border-b border-gray-800">
            Ingestor Status
          </h2>
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="text-left py-2 px-3 text-xs text-gray-500 uppercase">Ingestor</th>
                <th className="text-left py-2 px-3 text-xs text-gray-500 uppercase">Status</th>
                <th className="text-left py-2 px-3 text-xs text-gray-500 uppercase">Last Run</th>
                <th className="text-left py-2 px-3 text-xs text-gray-500 uppercase">Failures</th>
                <th className="text-left py-2 px-3 text-xs text-gray-500 uppercase">Avg Time</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(health.ingestors).map(([name, data]) => (
                <IngestorRow key={name} name={name} data={data} />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {loading && !health && (
        <div className="text-gray-500 text-center py-12">Loading...</div>
      )}
    </div>
  )
}
