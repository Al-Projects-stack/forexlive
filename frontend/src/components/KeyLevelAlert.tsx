import { useEffect } from 'react'
import toast from 'react-hot-toast'
import { WSMessage, Pair } from '../types'

interface KeyLevelAlertProps {
  lastMessage: WSMessage | null
  pair: Pair
}

export const KeyLevelAlert = ({ lastMessage, pair }: KeyLevelAlertProps) => {
  useEffect(() => {
    if (!lastMessage) return

    if (lastMessage.type === 'KEY_LEVEL_ALERT' && lastMessage.key_level_triggered) {
      const { level, direction } = lastMessage.key_level_triggered
      const digits = pair === 'USD/JPY' ? 3 : 5
      toast(
        `${pair} touched ${level.toFixed(digits)} (${direction})`,
        {
          duration: 5000,
          style: {
            background: '#1e3a5f',
            color: '#93c5fd',
            border: '1px solid #3b82f6',
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '13px',
          },
          icon: '🎯',
        }
      )
    }

    if (lastMessage.type === 'NEWS_WARNING' && lastMessage.news_warning) {
      const { event, minutes_away, impact } = lastMessage.news_warning
      if (impact === 'HIGH') {
        toast(
          `HIGH IMPACT: ${event} in ${minutes_away}m`,
          {
            duration: 10000,
            style: {
              background: '#450a0a',
              color: '#fca5a5',
              border: '1px solid #ef4444',
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '13px',
            },
            icon: '⚡',
          }
        )
      }
    }
  }, [lastMessage, pair])

  return null
}
