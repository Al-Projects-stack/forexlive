import { useState, useEffect } from 'react'
import { NewsEvent } from '../types'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const IMPACT_COLORS: Record<string, string> = {
  HIGH: 'text-red-400 border-red-500/30 bg-red-500/10',
  MEDIUM: 'text-amber-400 border-amber-500/30 bg-amber-500/10',
  LOW: 'text-gray-500 border-gray-700 bg-gray-800/50',
}

function formatLocalTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function sourceLabel(events: NewsEvent[]): string | null {
  const first = events[0]
  if (!first?.source) return null
  if (first.source === 'fallback') return 'Estimated schedule'
  return first.updated_at ? `ForexFactory · ${formatLocalTime(first.updated_at)}` : 'ForexFactory'
}

function formatCountdown(minutes: number): string {
  if (minutes < 0) return 'LIVE'
  if (minutes === 0) return 'NOW'
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}

export const NewsCalendar = () => {
  const [events, setEvents] = useState<NewsEvent[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        const res = await fetch(`${API_URL}/api/v1/news`)
        if (res.ok) {
          const data: NewsEvent[] = await res.json()
          setEvents(data)
        }
      } catch {
        // Silently fail — will retry
      } finally {
        setLoading(false)
      }
    }

    fetchEvents()
    // Refresh every minute
    const interval = setInterval(fetchEvents, 60_000)
    return () => clearInterval(interval)
  }, [])

  // Decrement countdowns every minute
  useEffect(() => {
    const interval = setInterval(() => {
      setEvents((prev) => prev.map((e) => ({ ...e, minutes_away: e.minutes_away - 1 })))
    }, 60_000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-gray-400 text-xs tracking-widest uppercase">News Calendar</span>
        {sourceLabel(events) && (
          <span
            className="text-[10px] text-gray-600 truncate"
            title={events[0]?.source === 'fallback' ? 'Live calendar unavailable, showing typical release times' : 'Live economic calendar'}
          >
            {sourceLabel(events)}
          </span>
        )}
      </div>

      {loading && <span className="text-gray-600 text-xs">Loading events...</span>}

      <div className="flex flex-col gap-1.5">
        {events.map((event, i) => (
          <div
            key={i}
            className={`flex items-start gap-2 px-2 py-2 rounded border text-xs ${IMPACT_COLORS[event.impact] ?? IMPACT_COLORS.LOW}`}
          >
            <div className="flex flex-col flex-1 min-w-0">
              <span className="font-medium truncate">{event.name}</span>
              <span className="text-gray-500 text-xs mt-0.5">
                {event.currency} · {formatLocalTime(event.scheduled_at)}
              </span>
              {(event.forecast || event.previous) && (
                <span className="text-gray-500 text-[11px] font-mono mt-0.5">
                  {event.forecast && <>F {event.forecast}</>}
                  {event.forecast && event.previous && ' · '}
                  {event.previous && <>P {event.previous}</>}
                </span>
              )}
            </div>
            <div className="flex flex-col items-end shrink-0">
              <span className="font-mono font-semibold">{formatCountdown(event.minutes_away)}</span>
              <span className="text-xs opacity-70">{event.impact}</span>
            </div>
          </div>
        ))}
        {!loading && events.length === 0 && (
          <span className="text-gray-600 text-xs">No more scheduled releases this week</span>
        )}
      </div>
    </div>
  )
}
