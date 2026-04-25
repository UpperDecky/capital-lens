import { useState, useEffect, useRef } from 'react'
import { api } from '../lib/api'

const READ_AT_KEY = 'cl_alerts_read_at'

export function useAlerts(token) {
  const [alerts, setAlerts]   = useState([])
  const [unread, setUnread]   = useState(0)
  const seenIds               = useRef(new Set())
  const isFirst               = useRef(true)

  function markRead() {
    setUnread(0)
    localStorage.setItem(READ_AT_KEY, new Date().toISOString())
  }

  useEffect(() => {
    // Skip polling when unauthenticated -- avoids 401 noise on the login page
    if (!token) return

    // Request browser notification permission (silently -- no-op if already granted/denied)
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission().catch(() => {})
    }

    async function poll() {
      try {
        const data = await api.getAlerts()
        if (!Array.isArray(data) || data.length === 0) return

        // Identify events we haven't seen in this session
        const newOnes = data.filter(a => !seenIds.current.has(a.id))
        newOnes.forEach(a => seenIds.current.add(a.id))

        setAlerts(data)

        // Unread = alerts that arrived after the last time the bell was opened
        const readAt = localStorage.getItem(READ_AT_KEY)
        setUnread(
          data.filter(a => !readAt || (a.occurred_at && a.occurred_at > readAt)).length
        )

        // Push browser notifications only for events that are truly new after first load
        if (!isFirst.current && newOnes.length > 0) {
          if ('Notification' in window && Notification.permission === 'granted') {
            newOnes.slice(0, 3).forEach(a => {
              try {
                new Notification('Capital Lens', {
                  body: (a.headline || '').slice(0, 120),
                  tag:  a.id,
                })
              } catch (_) {}
            })
          }
        }

        isFirst.current = false
      } catch (_) {}
    }

    poll()
    const id = setInterval(poll, 60_000)
    return () => clearInterval(id)
  }, [token])

  return { alerts, unread, markRead }
}
