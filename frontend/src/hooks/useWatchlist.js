import { useState, useCallback } from 'react'

const KEY = 'cl_watchlist'

function load() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || '[]')
  } catch {
    return []
  }
}

export function useWatchlist() {
  const [watchedIds, setWatchedIds] = useState(load)

  const toggle = useCallback((id) => {
    setWatchedIds(prev => {
      const next = prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
      localStorage.setItem(KEY, JSON.stringify(next))
      return next
    })
  }, [])

  const isWatched = useCallback((id) => watchedIds.includes(id), [watchedIds])

  return { watchedIds, toggle, isWatched }
}
