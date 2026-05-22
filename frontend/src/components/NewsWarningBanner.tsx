import { WSMessage } from '../types'
import { useEffect, useState } from 'react'

interface NewsWarningBannerProps {
  lastMessage: WSMessage | null
}

export const NewsWarningBanner = ({ lastMessage }: NewsWarningBannerProps) => {
  const [warning, setWarning] = useState<{ event: string; minutes_away: number } | null>(null)

  useEffect(() => {
    if (lastMessage?.type === 'NEWS_WARNING' && lastMessage.news_warning?.impact === 'HIGH') {
      setWarning({
        event: lastMessage.news_warning.event,
        minutes_away: lastMessage.news_warning.minutes_away,
      })
      // Auto-dismiss after 30 seconds
      const timer = setTimeout(() => setWarning(null), 30_000)
      return () => clearTimeout(timer)
    }
  }, [lastMessage])

  if (!warning) return null

  return (
    <div className="flex items-center justify-between px-4 py-2 bg-red-900/40 border-b border-red-500/50 text-red-300 text-xs font-mono animate-pulse">
      <span>⚡ HIGH IMPACT NEWS LIVE — {warning.event} — Volatility expected</span>
      <button onClick={() => setWarning(null)} className="text-red-500 hover:text-red-300 ml-4">✕</button>
    </div>
  )
}
