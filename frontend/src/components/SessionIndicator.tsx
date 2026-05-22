import { useState, useEffect } from 'react'
import { SessionInfo } from '../types'

// All times in SAST (UTC+2)
const SESSIONS: SessionInfo[] = [
  { name: 'Tokyo', active: false, start: '01:00', end: '09:00', color: 'bg-cyan-600' },
  { name: 'London', active: false, start: '10:00', end: '18:00', color: 'bg-blue-600' },
  { name: 'Overlap', active: false, start: '15:00', end: '18:00', color: 'bg-purple-600' },
  { name: 'New York', active: false, start: '15:00', end: '23:00', color: 'bg-indigo-600' },
]

function getSASTHour(): number {
  const now = new Date()
  // SAST = UTC+2
  const utcHour = now.getUTCHours()
  const utcMin = now.getUTCMinutes()
  return utcHour * 60 + utcMin + 120 // SAST minutes from midnight
}

function parseTime(t: string): number {
  const [h, m] = t.split(':').map(Number)
  return h * 60 + (m ?? 0)
}

function getActiveSessions(): SessionInfo[] {
  const nowMin = getSASTHour() % (24 * 60)
  return SESSIONS.map((s) => {
    const start = parseTime(s.start)
    let end = parseTime(s.end)
    if (end < start) end += 24 * 60
    const active = nowMin >= start && nowMin < end
    return { ...s, active }
  })
}

export const SessionIndicator = () => {
  const [sessions, setSessions] = useState<SessionInfo[]>(getActiveSessions())

  useEffect(() => {
    const interval = setInterval(() => setSessions(getActiveSessions()), 60_000)
    return () => clearInterval(interval)
  }, [])

  const now = new Date()
  const sastTime = new Date(now.getTime() + 2 * 3600_000)
  const timeStr = sastTime.toISOString().slice(11, 16) + ' SAST'

  return (
    <div className="flex items-center gap-3 px-4 py-2 bg-terminal-surface border-b border-terminal-border text-xs font-mono">
      <span className="text-gray-400">SESSIONS</span>
      {sessions.map((s) => (
        <div
          key={s.name}
          className={`flex items-center gap-1.5 px-3 py-1 rounded ${
            s.active
              ? `${s.color} text-white font-semibold`
              : 'bg-gray-800 text-gray-500'
          }`}
        >
          <span>{s.name}</span>
          <span className="opacity-70">{s.start}–{s.end}</span>
          {s.active && <span className="ml-1 w-1.5 h-1.5 rounded-full bg-white animate-pulse" />}
        </div>
      ))}
      <span className="ml-auto text-gray-400">{timeStr}</span>
    </div>
  )
}
