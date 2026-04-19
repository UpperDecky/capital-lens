import { useEffect, useRef } from 'react'
import { ScanBar } from './Illustrations'

export default function LoadMore({ hasMore, loading, onLoadMore }) {
  const ref = useRef(null)

  useEffect(() => {
    if (!hasMore || loading) return
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) onLoadMore() },
      { rootMargin: '200px' }
    )
    if (ref.current) observer.observe(ref.current)
    return () => observer.disconnect()
  }, [hasMore, loading, onLoadMore])

  if (!hasMore && !loading) return null

  return (
    <div ref={ref} className="py-10">
      {loading && (
        <div className="space-y-2">
          <ScanBar />
          <p className="text-center text-[10px] uppercase tracking-[0.1em] text-[#999] font-medium">
            Loading
          </p>
        </div>
      )}
    </div>
  )
}
